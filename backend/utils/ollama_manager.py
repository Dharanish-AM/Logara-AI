"""
Ollama model lifecycle manager.

Handles bootstrap, state tracking, and concurrent pull prevention for Ollama models.
"""

import asyncio
import logging
from typing import Optional

from core.settings import get_settings
from integrations.ollama import ollama_client

logger = logging.getLogger(__name__)


class OllamaModelManager:
    """
    Manages the lifecycle of Ollama models.
    
    States:
        - idle: Initial state, no operation in progress
        - checking: Verifying if model exists
        - pulling: Downloading model from registry
        - ready: Model is available and ready for use
        - failed: Bootstrap or pull operation failed
    """

    def __init__(self):
        self.model_name: str = get_settings().ollama_default_model
        self.status: str = "idle"
        self.progress: int = 0
        self.error: Optional[str] = None
        self._lock = asyncio.Lock()
        self._bootstrap_attempted = False

    async def bootstrap(self) -> None:
        """
        Bootstrap the Ollama model lifecycle.
        
        Checks if the configured model exists and pulls it if necessary.
        Uses asyncio.Lock to prevent concurrent pull attempts.
        """
        async with self._lock:
            if self._bootstrap_attempted:
                logger.debug("Bootstrap already attempted, skipping")
                return

            self._bootstrap_attempted = True

            try:
                if await self.check_model_exists():
                    self.status = "ready"
                    self.progress = 100
                    logger.info(f"Ollama model '{self.model_name}' is already available")
                else:
                    self.status = "pulling"
                    logger.info(f"Model '{self.model_name}' not found, starting pull...")
                    await self._pull_model_internal()
                    self.status = "ready"
                    self.progress = 100
                    logger.info(f"Successfully pulled model '{self.model_name}'")

            except asyncio.CancelledError:
                logger.warning("Bootstrap operation was cancelled")
                self.status = "failed"
                self.error = "Bootstrap operation was cancelled"
                raise

            except Exception as e:
                self.status = "failed"
                self.error = str(e)
                logger.error(f"Ollama bootstrap failed: {e}", exc_info=True)

    async def check_model_exists(self) -> bool:
        """
        Check if the configured model exists in Ollama.
        
        Returns:
            True if model is available, False otherwise.
        """
        try:
            self.status = "checking"
            models = await ollama_client.get_models()
            
            # Model names may have tags (e.g., "llama3:latest"), so we check if any model
            # starts with the configured model name
            exists = any(
                model.startswith(self.model_name)
                for model in models
            )
            
            if exists:
                logger.info(f"Model '{self.model_name}' found in available models")
            else:
                logger.warning(f"Model '{self.model_name}' not found. Available: {models}")
            
            return exists

        except Exception as e:
            logger.error(f"Error checking for model '{self.model_name}': {e}")
            raise

    async def _pull_model_internal(self) -> None:
        """
        Internal method to pull the model.
        
        Raises:
            Exception: If pull operation fails.
        """
        try:
            result = await ollama_client.pull_model(self.model_name)
            if result.get("status") != "success":
                raise Exception(f"Pull operation returned non-success status: {result}")
            self.progress = 100
        except Exception as e:
            logger.error(f"Failed to pull model '{self.model_name}': {e}")
            raise

    def get_status(self) -> dict:
        """
        Get current status of the Ollama model lifecycle.
        
        Returns:
            Dictionary with status, model name, progress, and optional error.
        """
        return {
            "status": self.status,
            "model": self.model_name,
            "progress": self.progress,
            "error": self.error,
        }

    def reset(self) -> None:
        """
        Reset the manager state (useful for testing).
        """
        self.status = "idle"
        self.progress = 0
        self.error = None
        self._bootstrap_attempted = False
