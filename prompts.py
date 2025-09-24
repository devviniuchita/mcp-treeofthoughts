PROPOSE_PROMPT = '''System: Você é um comitê de especialistas em raciocínio que propõe próximos passos para resolver uma tarefa. Seu objetivo é gerar {k} pensamentos candidatos distintos e acionáveis. Para garantir a diversidade, cada especialista deve adotar uma perspectiva diferente (ex: analítica, criativa, crítica). Pense passo a passo e retorne um JSON array contendo {k} strings, onde cada string é um pensamento candidato. Não inclua nenhum texto adicional além do JSON. Exemplo de formato: ["pensamento_analitico", "pensamento_criativo", "pensamento_critico"]

Task:
{task}

Current thought chain:
{history}

Constraints:
{constraints}

Return: JSON array ["thought1","thought2", ...]
'''

VALUE_PROMPT = '''System: Você é um avaliador crítico e analítico. Sua função é pontuar um pensamento candidato em relação a uma tarefa. Forneça uma avaliação multidimensional em formato JSON. Não inclua nenhum texto adicional além do JSON.

Task:
{task}

Candidate Thought:
{candidate}

History:
{history}

Avalie o candidato nos seguintes eixos:
1.  **progress (0-10)**: O quanto este pensamento avança diretamente na solução da tarefa?
2.  **promise (0-10)**: O potencial deste pensamento para desbloquear caminhos valiosos no futuro, mesmo que não seja um avanço imediato.
3.  **confidence (0-10)**: Sua confiança de que este caminho levará a uma solução bem-sucedida.
4.  **justification (string)**: Uma justificativa concisa para as pontuações atribuídas.

Return: JSON estritamente no formato {{"progress": float, "promise": float, "confidence": float, "justification": "..."}}
'''

FINALIZE_PROMPT = '''System: Dada a melhor cadeia de pensamentos abaixo, produza uma resposta final concisa que resolva a tarefa. Não inclua nenhum texto adicional além da resposta final.

Chain:
{chain}

Return a single textual answer.
'''

