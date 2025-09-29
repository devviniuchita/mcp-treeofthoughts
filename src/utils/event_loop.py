"""Event loop utilities for background task management."""

import asyncio
import atexit
import threading

from typing import Optional


class BackgroundEventLoop:
    """Manages background event loop for async tasks."""

    def __init__(self) -> None:
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.thread: Optional[threading.Thread] = None

    def get_or_create_loop(self) -> asyncio.AbstractEventLoop:
        """Get existing loop or create new background loop."""
        if self.loop is None or self.loop.is_closed():
            self._create_background_loop()

        if self.loop is None:
            raise RuntimeError("Failed to initialize background event loop")

        return self.loop

    def _create_background_loop(self) -> None:
        """Create new event loop in background thread."""
        self.loop = asyncio.new_event_loop()

        def run_loop():
            asyncio.set_event_loop(self.loop)
            if self.loop:
                self.loop.run_forever()

        self.thread = threading.Thread(target=run_loop, daemon=True)
        self.thread.start()

    def shutdown(self) -> None:
        """Shutdown background loop gracefully."""
        if self.loop and self.loop.is_running():
            self.loop.call_soon_threadsafe(self.loop.stop)

        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1)


# Global background loop instance
_background_loop = BackgroundEventLoop()


def get_or_create_event_loop() -> asyncio.AbstractEventLoop:
    """Get or create background event loop for async tasks."""
    return _background_loop.get_or_create_loop()


def shutdown_background_loop() -> None:
    """Shutdown background event loop on process exit."""
    _background_loop.shutdown()


# Register cleanup on exit
atexit.register(shutdown_background_loop)
