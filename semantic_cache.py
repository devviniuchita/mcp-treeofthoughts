import faiss
import numpy as np
import pickle
import os
import time
import threading
from pathlib import Path
from typing import List, Dict, Any, Optional, Set
from collections import defaultdict, OrderedDict
from src.llm_client import get_embeddings
import logging
import hashlib

logger = logging.getLogger(__name__)

class SemanticCache:
    # Dimensões conhecidas por modelo
    KNOWN_DIMENSIONS = {
        "gemini-embedding-001": 3072,
        "text-embedding-ada-002": 1536,
        "text-embedding-3-small": 1536,
        "text-embedding-3-large": 3072
    }
    
    # Limites de dimensão para validação
    MIN_DIMENSION = 256
    MAX_DIMENSION = 4096
    
    def __init__(self, 
                 embedding_model_name: str = "gemini-embedding-001", 
                 dimension: Optional[int] = None,
                 google_api_key: Optional[str] = None,
                 cache_dir: str = "cache",
                 cache_name: str = "semantic_cache",
                 max_size: int = 10000,
                 auto_save_interval: int = 100):
        """
        Cache semântico com persistência inteligente e gestão de memória
        
        Args:
            embedding_model_name: Nome do modelo de embedding
            dimension: Dimensão dos embeddings (auto-detecta se None)
            google_api_key: Chave da API do Google (opcional)
            cache_dir: Diretório para armazenar o cache
            cache_name: Nome base dos arquivos de cache
            max_size: Tamanho máximo do cache (política LFU)
            auto_save_interval: Salva após N adições
        """
        self.embedding_model_name = embedding_model_name
        self.embeddings_model = get_embeddings(model=embedding_model_name, google_api_key=google_api_key)
        
        # Determinar dimensão inteligentemente
        self.dimension = self._determine_dimension(dimension)
        
        self.cache_dir = Path(cache_dir)
        self.cache_name = cache_name
        self.max_size = max_size
        self.auto_save_interval = auto_save_interval
        
        # Caminhos dos arquivos
        self.index_path = self.cache_dir / f"{cache_name}.index"
        self.metadata_path = self.cache_dir / f"{cache_name}.pkl"
        
        # Estruturas principais
        self.index = faiss.IndexFlatIP(self.dimension)
        self.texts = []
        self.metadata = []
        
        # Controle de duplicatas e frequência (LFU)
        self.text_to_index: Dict[str, int] = {}  # Mapeamento texto -> índice
        self.access_count: Dict[int, int] = defaultdict(int)  # Contador de acessos
        self.access_order = OrderedDict()  # Ordem de acesso para tie-breaking
        
        # Controle de persistência
        self.unsaved_changes = 0
        self.last_save_time = time.time()
        self._lock = threading.RLock()  # Thread safety
        
        # Estruturas para otimizações
        self._embedding_cache: Dict[str, np.ndarray] = {}  # Cache de embeddings
        self._large_texts_store: Dict[str, str] = {}  # Armazenamento para textos longos
        
        # Criar diretório e carregar cache
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._load_cache()
        
        logger.info(f"Cache inicializado: {len(self.texts)} itens, dimensão {self.dimension}")

    def _determine_dimension(self, provided_dimension: Optional[int]) -> int:
        """Determina dimensão do embedding inteligentemente"""
        if provided_dimension is not None:
            if not (self.MIN_DIMENSION <= provided_dimension <= self.MAX_DIMENSION):
                raise ValueError(f"Dimensão deve estar entre {self.MIN_DIMENSION} e {self.MAX_DIMENSION}")
            return provided_dimension
        
        # Tentar dimensão conhecida primeiro
        if self.embedding_model_name in self.KNOWN_DIMENSIONS:
            return self.KNOWN_DIMENSIONS[self.embedding_model_name]
        
        # Auto-detectar fazendo uma chamada de teste
        try:
            logger.info("Auto-detectando dimensão do modelo...")
            test_embedding = self.embeddings_model.embed_query("test")
            detected_dim = len(np.array(test_embedding).flatten())
            
            if not (self.MIN_DIMENSION <= detected_dim <= self.MAX_DIMENSION):
                raise ValueError(f"Dimensão detectada ({detected_dim}) fora dos limites seguros")
                
            logger.info(f"Dimensão auto-detectada: {detected_dim}")
            return detected_dim
            
        except Exception as e:
            logger.warning(f"Falha na auto-detecção: {e}. Usando dimensão padrão.")
            return self.KNOWN_DIMENSIONS["gemini-embedding-001"]

    def _get_embedding(self, text: str, retry_count: int = 2) -> np.ndarray:
        """Gera embedding normalizado com retry para robustez"""
        # Verificar se o embedding já está no cache
        if text in self._embedding_cache:
            return self._embedding_cache[text]
        
        for attempt in range(retry_count + 1):
            try:
                raw_embedding = self.embeddings_model.embed_query(text)
                logger.debug(f"Raw embedding type: {type(raw_embedding)}, length: {len(raw_embedding)}")
                
                vec = np.array(raw_embedding).astype("float32")
                
                # Garantir que o embedding é 1D
                if vec.ndim == 2 and vec.shape[0] == 1:
                    vec = vec.flatten()
                elif vec.ndim != 1:
                    raise ValueError(f"Unexpected embedding shape: {vec.shape}. Expected 1D array after flattening.")

                if vec.shape[0] != self.dimension:
                    raise ValueError(f"Embedding dimension mismatch! Expected {self.dimension}, got {vec.shape[0]} after flattening.")

                # Verificar norma e normalizar
                norm = np.linalg.norm(vec)
                if norm == 0:
                    if attempt < retry_count:
                        logger.warning(f"Embedding com norma zero (tentativa {attempt + 1}), tentando novamente...")
                        delay = (2 ** attempt) * 0.1  # Backoff exponencial
                        time.sleep(delay)
                        continue
                    else:
                        raise ValueError(f"Embedding com norma zero após {retry_count + 1} tentativas. Texto: '{text[:50]}...'")
                
                # Normalizar e armazenar no cache
                normalized_embedding = (vec / norm).astype("float32")
                self._embedding_cache[text] = normalized_embedding
                return normalized_embedding
                
            except Exception as e:
                if attempt < retry_count:
                    logger.warning(f"Erro no embedding (tentativa {attempt + 1}): {e}")
                    delay = (2 ** attempt) * 0.1  # Backoff exponencial
                    time.sleep(delay)
                    continue
                else:
                    logger.error(f"Falha definitiva no embedding após {retry_count + 1} tentativas: {e}")
                    raise

    def _get_original_text(self, stored_text: str) -> str:
        """Converte texto armazenado para texto original"""
        if stored_text.startswith("__LONG_TEXT_") and stored_text.endswith("__"):
            text_hash = stored_text[12:-2]  # "__LONG_TEXT_" tem 12 caracteres
            return self._large_texts_store.get(text_hash, stored_text)
        return stored_text

    def _load_cache(self) -> None:
        """Carrega cache do disco com reconstrução de índices auxiliares"""
        try:
            if self.index_path.exists() and self.metadata_path.exists():
                # Carregar índice FAISS
                self.index = faiss.read_index(str(self.index_path))
                
                # Carregar metadados
                with open(self.metadata_path, 'rb') as f:
                    cache_data = pickle.load(f)
                    self.texts = cache_data.get('texts', [])
                    self.metadata = cache_data.get('metadata', [])
                    self.access_count = cache_data.get('access_count', defaultdict(int))
                    self._large_texts_store = cache_data.get('large_texts_store', {})
                    
                # Reconstruir índices auxiliares
                self._rebuild_auxiliary_indexes()
                
                logger.info(f"Cache carregado: {len(self.texts)} itens")
            else:
                logger.info("Nenhum cache existente encontrado, iniciando vazio")
                
        except Exception as e:
            logger.warning(f"Erro ao carregar cache: {e}. Iniciando com cache vazio.")
            self._reset_cache()

    def _rebuild_auxiliary_indexes(self) -> None:
        """Reconstrói índices auxiliares após carregamento"""
        self.text_to_index.clear()
        self.access_order.clear()
        
        for i, stored_text in enumerate(self.texts):
            original_text = self._get_original_text(stored_text)
            self.text_to_index[original_text] = i
            self.access_order[i] = self.access_count.get(i, 0)

    def _reset_cache(self) -> None:
        """Reseta completamente o cache"""
        self.index = faiss.IndexFlatIP(self.dimension)
        self.texts = []
        self.metadata = []
        self.text_to_index.clear()
        self.access_count.clear()
        self.access_order.clear()
        self._embedding_cache.clear()
        self._large_texts_store.clear()

    def _save_cache(self) -> None:
        """Salva cache no disco com dados auxiliares"""
        try:
            # Salvar índice FAISS
            faiss.write_index(self.index, str(self.index_path))
            
            # Salvar metadados incluindo contadores
            cache_data = {
                'texts': self.texts,
                'metadata': self.metadata,
                'access_count': dict(self.access_count),
                'large_texts_store': self._large_texts_store
            }
            with open(self.metadata_path, 'wb') as f:
                pickle.dump(cache_data, f, protocol=pickle.HIGHEST_PROTOCOL)
                
            self.unsaved_changes = 0
            self.last_save_time = time.time()
            logger.debug(f"Cache salvo: {len(self.texts)} itens")
            
        except Exception as e:
            logger.error(f"Erro ao salvar cache: {e}")

    def _should_auto_save(self) -> bool:
        """Determina se deve fazer auto-save"""
        return (self.unsaved_changes >= self.auto_save_interval or 
                time.time() - self.last_save_time > 300)

    def _evict_lfu_items(self, num_to_evict: int) -> None:
        """Remove itens usando política LFU (Least Frequently Used)"""
        if num_to_evict <= 0:
            return
            
        # Criar lista de (índice, frequência, ordem_acesso) para ordenação
        items_with_freq = []
        for i in range(len(self.texts)):
            freq = self.access_count[i]
            order = self.access_order.get(i, 0)
            items_with_freq.append((i, freq, order))
        
        # Ordenar por frequência (crescente) e ordem (crescente para tie-breaking)
        items_with_freq.sort(key=lambda x: (x[1], x[2]))
        
        # Remover os menos frequentes
        indices_to_remove = [item[0] for item in items_with_freq[:num_to_evict]]
        indices_to_remove.sort(reverse=True)
        
        for idx in indices_to_remove:
            stored_text = self.texts[idx]
            original_text = self._get_original_text(stored_text)
            
            # Verificar se é um texto longo e remover do armazenamento
            if stored_text.startswith("__LONG_TEXT_") and stored_text.endswith("__"):
                text_hash = stored_text[12:-2]
                if text_hash in self._large_texts_store:
                    del self._large_texts_store[text_hash]
            
            # Remover do cache de embeddings
            if original_text in self._embedding_cache:
                del self._embedding_cache[original_text]
            
            # Remover das estruturas
            del self.texts[idx]
            del self.metadata[idx]
            if original_text in self.text_to_index:
                del self.text_to_index[original_text]
            if idx in self.access_count:
                del self.access_count[idx]
            if idx in self.access_order:
                del self.access_order[idx]
        
        # Reconstruir índice FAISS
        self._rebuild_faiss_index()
        
        # Atualizar mapeamentos
        self._rebuild_auxiliary_indexes()
        
        logger.info(f"Removidos {num_to_evict} itens menos frequentes (LFU)")

    def _rebuild_faiss_index(self) -> None:
        """Reconstrói o índice FAISS com os embeddings atuais"""
        if not self.texts:
            self.index = faiss.IndexFlatIP(self.dimension)
            return
            
        # Usar embeddings do cache quando disponíveis
        embeddings = []
        for stored_text in self.texts:
            original_text = self._get_original_text(stored_text)
            
            if original_text in self._embedding_cache:
                embedding = self._embedding_cache[original_text]
            else:
                embedding = self._get_embedding(original_text)
            embeddings.append(embedding)
        
        # Recriar índice
        self.index = faiss.IndexFlatIP(self.dimension)
        if embeddings:
            embeddings_array = np.vstack(embeddings)
            self.index.add(embeddings_array)

    def add(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Adiciona texto ao cache com controle de duplicatas e gestão inteligente
        
        Args:
            text: Texto a ser adicionado
            metadata: Metadados opcionais associados ao texto
            
        Returns:
            bool: True se foi adicionado, False se já existia
        """
        with self._lock:
            # Verificar duplicata
            if text in self.text_to_index:
                existing_idx = self.text_to_index[text]
                self.access_count[existing_idx] += 1
                self.access_order[existing_idx] = time.time()
                logger.debug(f"Texto já existe no cache (índice {existing_idx})")
                return False
            
            try:
                # Verificar se precisa fazer evicção
                if len(self.texts) >= self.max_size:
                    self._evict_lfu_items(1)
                
                # Lidar com textos longos
                stored_text = text
                if len(text) > 1000:
                    text_hash = hashlib.md5(text.encode()).hexdigest()
                    self._large_texts_store[text_hash] = text
                    stored_text = f"__LONG_TEXT_{text_hash}__"
                
                # Gerar embedding e adicionar
                embedding = self._get_embedding(text).reshape(1, -1)
                self.index.add(embedding)
                
                # Adicionar às estruturas
                new_idx = len(self.texts)
                self.texts.append(stored_text)
                self.metadata.append(metadata or {})
                self.text_to_index[text] = new_idx
                self.access_count[new_idx] = 1
                self.access_order[new_idx] = time.time()
                
                # Controlar persistência
                self.unsaved_changes += 1
                if self._should_auto_save():
                    self._save_cache()
                
                logger.debug(f"Texto adicionado ao cache (índice {new_idx})")
                return True
                
            except Exception as e:
                logger.error(f"Erro ao adicionar item ao cache: {e}")
                raise

    def search(self, query_text: str, k: int = 1, min_score: float = 0.75) -> List[Dict[str, Any]]:
        """
        Busca textos similares no cache com atualização de frequência
        
        Args:
            query_text: Texto da consulta
            k: Número máximo de resultados
            min_score: Score mínimo (similaridade cosseno)
            
        Returns:
            Lista de resultados com texto, metadados e score
        """
        with self._lock:
            try:
                if self.index.ntotal == 0:
                    logger.debug("Cache vazio, retornando lista vazia")
                    return []
                    
                q = self._get_embedding(query_text).reshape(1, -1)
                scores, indices = self.index.search(q, min(k, self.index.ntotal))
                
                results = []
                current_time = time.time()
                
                for i, idx in enumerate(indices[0]):
                    if idx == -1:
                        continue
                        
                    score = float(scores[0][i])
                    if score >= min_score:
                        # Atualizar estatísticas de acesso
                        self.access_count[idx] += 1
                        self.access_order[idx] = current_time
                        
                        # Recuperar o texto original
                        stored_text = self.texts[idx]
                        original_text = self._get_original_text(stored_text)
                        
                        results.append({
                            "text": original_text,
                            "metadata": self.metadata[idx],
                            "score": score,
                            "access_count": self.access_count[idx]
                        })
                        
                logger.debug(f"Busca retornou {len(results)} resultados")
                return results
                
            except Exception as e:
                logger.error(f"Erro na busca: {e}")
                return []

    def force_save(self) -> None:
        """Força persistência imediata"""
        with self._lock:
            self._save_cache()

    def size(self) -> int:
        """Retorna o número de itens no cache"""
        return len(self.texts)

    def clear_cache(self) -> None:
        """Remove todos os itens do cache e arquivos de persistência"""
        with self._lock:
            try:
                self._reset_cache()
                
                if self.index_path.exists():
                    self.index_path.unlink()
                if self.metadata_path.exists():
                    self.metadata_path.unlink()
                    
                logger.info("Cache limpo completamente")
                
            except Exception as e:
                logger.error(f"Erro ao limpar cache: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas detalhadas do cache"""
        with self._lock:
            total_accesses = sum(self.access_count.values())
            avg_accesses = total_accesses / len(self.texts) if self.texts else 0
            
            # Estatísticas de compressão
            compressed_count = sum(1 for text in self.texts 
                                  if text.startswith("__LONG_TEXT_") and text.endswith("__"))
            compression_ratio = compressed_count / len(self.texts) if self.texts else 0
            
            return {
                "total_items": len(self.texts),
                "dimension": self.dimension,
                "max_size": self.max_size,
                "unsaved_changes": self.unsaved_changes,
                "total_accesses": total_accesses,
                "avg_accesses_per_item": round(avg_accesses, 2),
                "embedding_cache_size": len(self._embedding_cache),
                "compressed_texts": compressed_count,
                "compression_ratio": round(compression_ratio, 3),
                "large_texts_store_size": len(self._large_texts_store),
                "index_size_mb": self.index_path.stat().st_size / (1024*1024) if self.index_path.exists() else 0,
                "metadata_size_mb": self.metadata_path.stat().st_size / (1024*1024) if self.metadata_path.exists() else 0,
                "cache_dir": str(self.cache_dir),
                "cache_exists": self.index_path.exists() and self.metadata_path.exists(),
                "model_name": self.embedding_model_name
            }

    def get_top_accessed_items(self, n: int = 10) -> List[Dict[str, Any]]:
        """Retorna os N itens mais acessados"""
        with self._lock:
            items = []
            for i, stored_text in enumerate(self.texts):
                original_text = self._get_original_text(stored_text)
                display_text = original_text[:100] + "..." if len(original_text) > 100 else original_text
                
                items.append({
                    "text": display_text,
                    "access_count": self.access_count[i],
                    "metadata": self.metadata[i]
                })
            
            return sorted(items, key=lambda x: x["access_count"], reverse=True)[:n]

    def __del__(self):
        """Destrutor garante que o cache seja salvo"""
        try:
            if hasattr(self, 'texts') and hasattr(self, 'unsaved_changes'):
                if len(self.texts) > 0 and self.unsaved_changes > 0:
                    self._save_cache()
        except:
            pass