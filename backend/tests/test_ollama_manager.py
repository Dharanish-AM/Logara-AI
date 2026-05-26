"""
Tests for Ollama model lifecycle manager.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import logging

from utils.ollama_manager import OllamaModelManager
from core.settings import Settings

logger = logging.getLogger(__name__)

pytestmark = pytest.mark.anyio


@pytest.fixture
def ollama_manager():
    """Provide a fresh OllamaModelManager instance for each test."""
    manager = OllamaModelManager()
    manager.reset()
    return manager


class TestOllamaModelManagerStateTransitions:
    """Test state machine transitions for model bootstrap."""

    async def test_model_already_exists_transitions_to_ready(self, ollama_manager):
        """
        When model already exists, bootstrap should:
        - Check model exists
        - Transition to ready state
        - Set progress to 100
        """
        with patch("utils.ollama_manager.ollama_client.get_models") as mock_get_models:
            mock_get_models.return_value = ["llama3", "mistral"]
            
            await ollama_manager.bootstrap()
            
            assert ollama_manager.status == "ready"
            assert ollama_manager.progress == 100
            assert ollama_manager.error is None


    async def test_missing_model_triggers_pull_transitions_to_ready(self, ollama_manager):
        """
        When model is missing, bootstrap should:
        - Detect missing model
        - Pull the model
        - Transition through pulling -> ready states
        """
        with patch("utils.ollama_manager.ollama_client.get_models") as mock_get_models, \
             patch("utils.ollama_manager.ollama_client.pull_model") as mock_pull:
            
            mock_get_models.return_value = ["mistral"]  # llama3 not present
            mock_pull.return_value = {"status": "success", "model": "llama3", "data": {}}
            
            await ollama_manager.bootstrap()
            
            assert ollama_manager.status == "ready"
            assert ollama_manager.progress == 100
            assert ollama_manager.error is None
            mock_pull.assert_called_once_with("llama3")


    async def test_pull_failure_transitions_to_failed(self, ollama_manager):
        """
        When pull operation fails, bootstrap should:
        - Attempt to pull model
        - Catch exception
        - Transition to failed state
        - Store error message
        """
        with patch("utils.ollama_manager.ollama_client.get_models") as mock_get_models, \
             patch("utils.ollama_manager.ollama_client.pull_model") as mock_pull:
            
            mock_get_models.return_value = []  # Model not present
            mock_pull.side_effect = Exception("Network error: connection refused")
            
            await ollama_manager.bootstrap()
            
            assert ollama_manager.status == "failed"
            assert ollama_manager.error is not None
            assert "Network error" in ollama_manager.error


    async def test_ollama_unavailable_transitions_to_failed(self, ollama_manager):
        """
        When Ollama is unavailable, bootstrap should:
        - Fail to check models
        - Transition to failed state
        - Store error
        """
        with patch("utils.ollama_manager.ollama_client.get_models") as mock_get_models:
            mock_get_models.side_effect = Exception("Ollama unreachable")
            
            await ollama_manager.bootstrap()
            
            assert ollama_manager.status == "failed"
            assert ollama_manager.error is not None
            assert "Ollama unreachable" in ollama_manager.error


class TestConcurrencyAndDuplicatePrevention:
    """Test concurrent access and duplicate prevention."""

    async def test_duplicate_bootstrap_attempts_prevented(self, ollama_manager):
        """
        When bootstrap is called multiple times concurrently,
        only one operation should execute (lock prevents duplicates).
        """
        with patch("utils.ollama_manager.ollama_client.get_models") as mock_get_models, \
             patch("utils.ollama_manager.ollama_client.pull_model") as mock_pull:
            
            mock_get_models.return_value = []
            mock_pull.return_value = {"status": "success", "model": "llama3", "data": {}}
            
            # Call bootstrap multiple times concurrently
            await asyncio.gather(
                ollama_manager.bootstrap(),
                ollama_manager.bootstrap(),
                ollama_manager.bootstrap(),
            )
            
            # pull_model should only be called once due to lock
            assert mock_pull.call_count == 1
            assert ollama_manager.status == "ready"


    async def test_sequential_bootstrap_calls_are_idempotent(self, ollama_manager):
        """
        After first bootstrap completes, subsequent calls should be no-ops.
        """
        with patch("utils.ollama_manager.ollama_client.get_models") as mock_get_models, \
             patch("utils.ollama_manager.ollama_client.pull_model") as mock_pull:
            
            mock_get_models.return_value = []
            mock_pull.return_value = {"status": "success", "model": "llama3", "data": {}}
            
            # First bootstrap
            await ollama_manager.bootstrap()
            assert ollama_manager.status == "ready"
            assert mock_pull.call_count == 1
            
            # Second bootstrap (should be no-op)
            await ollama_manager.bootstrap()
            assert mock_pull.call_count == 1  # Still 1, not incremented


class TestStatusEndpoint:
    """Test status reporting functionality."""

    def test_get_status_returns_correct_structure(self, ollama_manager):
        """Status endpoint should return complete status information."""
        ollama_manager.status = "pulling"
        ollama_manager.progress = 50
        ollama_manager.error = None
        
        status = ollama_manager.get_status()
        
        assert "status" in status
        assert "model" in status
        assert "progress" in status
        assert "error" in status
        assert status["status"] == "pulling"
        assert status["progress"] == 50
        assert status["model"] == "llama3"  # default from settings
        assert status["error"] is None


    def test_get_status_includes_error_when_failed(self, ollama_manager):
        """Status should include error message when operation fails."""
        ollama_manager.status = "failed"
        ollama_manager.error = "Connection timeout"
        
        status = ollama_manager.get_status()
        
        assert status["status"] == "failed"
        assert status["error"] == "Connection timeout"


class TestCheckModelExists:
    """Test model existence checking."""

    async def test_check_model_exists_returns_true_when_present(self, ollama_manager):
        """Should return True when model name matches available model."""
        with patch("utils.ollama_manager.ollama_client.get_models") as mock_get_models:
            mock_get_models.return_value = ["llama3", "llama3:latest", "mistral"]
            
            exists = await ollama_manager.check_model_exists()
            
            assert exists is True


    async def test_check_model_exists_returns_false_when_missing(self, ollama_manager):
        """Should return False when model is not in available models."""
        with patch("utils.ollama_manager.ollama_client.get_models") as mock_get_models:
            mock_get_models.return_value = ["mistral", "neural-chat"]
            
            exists = await ollama_manager.check_model_exists()
            
            assert exists is False


    async def test_check_model_exists_handles_tagged_models(self, ollama_manager):
        """Should match models with tags (e.g., llama3:latest)."""
        with patch("utils.ollama_manager.ollama_client.get_models") as mock_get_models:
            mock_get_models.return_value = ["llama3:latest", "mistral:7b"]
            
            exists = await ollama_manager.check_model_exists()
            
            assert exists is True


    async def test_check_model_exists_raises_on_api_error(self, ollama_manager):
        """Should raise exception when API call fails."""
        with patch("utils.ollama_manager.ollama_client.get_models") as mock_get_models:
            mock_get_models.side_effect = Exception("API error")
            
            with pytest.raises(Exception):
                await ollama_manager.check_model_exists()


class TestReset:
    """Test state reset functionality."""

    def test_reset_clears_all_state(self, ollama_manager):
        """Reset should clear all state back to initial values."""
        ollama_manager.status = "ready"
        ollama_manager.progress = 100
        ollama_manager.error = "Some error"
        ollama_manager._bootstrap_attempted = True
        
        ollama_manager.reset()
        
        assert ollama_manager.status == "idle"
        assert ollama_manager.progress == 0
        assert ollama_manager.error is None
        assert ollama_manager._bootstrap_attempted is False


class TestInitialization:
    """Test manager initialization."""

    def test_ollama_manager_initializes_with_default_model(self, ollama_manager):
        """Manager should initialize with model name from settings."""
        assert ollama_manager.model_name == "llama3"
        assert ollama_manager.status == "idle"
        assert ollama_manager.progress == 0
        assert ollama_manager.error is None
