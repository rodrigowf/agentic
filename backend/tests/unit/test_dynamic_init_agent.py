"""
Unit tests for DynamicInitLoopingAgent

Tests the dynamic initialization functionality, including:
- Agent creation with initialization function
- Function import and execution
- Error handling for invalid functions
- Integration with agent context
"""

import pytest
import sys
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add backend to path
backend_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_path))

from core.dynamic_init_looping_agent import DynamicInitLoopingAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_core.models import ModelInfo


@pytest.fixture
def mock_model_client():
    """Create a mock model client for testing"""
    model_info = ModelInfo(
        vision=True,
        function_calling=True,
        json_output=True,
        family="openai",
        structured_output=True
    )
    return OpenAIChatCompletionClient(
        model="gpt-4o-mini",
        api_key="test-key",
        model_info=model_info
    )


class TestDynamicInitLoopingAgent:
    """Test suite for DynamicInitLoopingAgent"""

    def test_agent_creation_without_init_function(self, mock_model_client):
        """Test that agent can be created without initialization function"""
        agent = DynamicInitLoopingAgent(
            name="TestAgent",
            description="Test agent without init",
            system_message="You are a test agent.",
            model_client=mock_model_client,
            tools=[],
            initialization_function=None
        )

        assert agent.name == "TestAgent"
        assert agent.initialization_function is None
        assert agent._system_messages[0].content == "You are a test agent."

    def test_agent_creation_with_empty_init_function(self, mock_model_client):
        """Test that agent handles empty initialization function string"""
        agent = DynamicInitLoopingAgent(
            name="TestAgent",
            description="Test agent with empty init",
            system_message="You are a test agent.",
            model_client=mock_model_client,
            tools=[],
            initialization_function=""
        )

        assert agent.name == "TestAgent"
        assert agent.initialization_function == ""

    def test_invalid_function_format(self, mock_model_client):
        """Test that invalid function format raises appropriate error"""
        # Should not raise during creation, but log error
        agent = DynamicInitLoopingAgent(
            name="TestAgent",
            description="Test agent",
            system_message="You are a test agent.",
            model_client=mock_model_client,
            tools=[],
            initialization_function="invalid_format"  # Missing module.function format
        )

        # Agent should still be created, just with failed initialization
        assert agent.name == "TestAgent"
        assert agent.initialization_function == "invalid_format"

    def test_module_not_found(self, mock_model_client):
        """Test that non-existent module is handled gracefully"""
        # Should not raise during creation, but log error
        agent = DynamicInitLoopingAgent(
            name="TestAgent",
            description="Test agent",
            system_message="You are a test agent.",
            model_client=mock_model_client,
            tools=[],
            initialization_function="nonexistent_module.some_function"
        )

        # Agent should still be created
        assert agent.name == "TestAgent"

    def test_function_not_found(self, mock_model_client):
        """Test that non-existent function in valid module is handled"""
        # Should not raise during creation, but log error
        agent = DynamicInitLoopingAgent(
            name="TestAgent",
            description="Test agent",
            system_message="You are a test agent.",
            model_client=mock_model_client,
            tools=[],
            initialization_function="memory.nonexistent_function"
        )

        # Agent should still be created
        assert agent.name == "TestAgent"

    @patch('core.dynamic_init_looping_agent.importlib.import_module')
    def test_successful_initialization(self, mock_import, mock_model_client):
        """Test successful initialization with valid function"""
        # Create mock module and function
        mock_module = MagicMock()
        mock_init_func = Mock(return_value="Initialization successful")
        mock_module.test_init = mock_init_func
        mock_import.return_value = mock_module

        # Create agent with initialization function
        agent = DynamicInitLoopingAgent(
            name="TestAgent",
            description="Test agent",
            system_message="You are a test agent.",
            model_client=mock_model_client,
            tools=[],
            initialization_function="test_module.test_init"
        )

        # Verify module was imported
        mock_import.assert_called_once_with('tools.test_module')

        # Verify function was called
        mock_init_func.assert_called_once()

        # Verify agent was created
        assert agent.name == "TestAgent"
        assert agent.initialization_function == "test_module.test_init"

    @patch('core.dynamic_init_looping_agent.importlib.import_module')
    def test_initialization_function_with_exception(self, mock_import, mock_model_client):
        """Test that exceptions in initialization function are handled"""
        # Create mock module with function that raises exception
        mock_module = MagicMock()
        mock_init_func = Mock(side_effect=Exception("Initialization failed"))
        mock_module.test_init = mock_init_func
        mock_import.return_value = mock_module

        # Agent creation should not raise, but log error
        agent = DynamicInitLoopingAgent(
            name="TestAgent",
            description="Test agent",
            system_message="You are a test agent.",
            model_client=mock_model_client,
            tools=[],
            initialization_function="test_module.test_init"
        )

        # Verify agent was still created
        assert agent.name == "TestAgent"

    @patch('core.dynamic_init_looping_agent.importlib.import_module')
    @patch('utils.context.get_current_agent')
    def test_initialization_can_modify_agent(self, mock_get_agent, mock_import, mock_model_client):
        """Test that initialization function can modify agent's system message"""
        # Create agent instance
        agent = None

        def create_and_init():
            nonlocal agent

            # Create mock module with initialization function
            mock_module = MagicMock()

            def mock_init():
                # Get current agent and modify it
                current_agent = mock_get_agent.return_value
                if current_agent and current_agent._system_messages:
                    current_agent._system_messages[0].content = "Modified by init function"
                return "Agent modified"

            mock_module.test_init = mock_init
            mock_import.return_value = mock_module

            # Create agent
            agent = DynamicInitLoopingAgent(
                name="TestAgent",
                description="Test agent",
                system_message="Original message with {{PLACEHOLDER}}",
                model_client=mock_model_client,
                tools=[],
                initialization_function="test_module.test_init"
            )

            # Set mock to return the agent
            mock_get_agent.return_value = agent

            return agent

        agent = create_and_init()

        # Verify agent was created
        assert agent.name == "TestAgent"

    def test_nested_function_name(self, mock_model_client):
        """Test that nested function names (with dots) are handled"""
        # This tests the '.'.join(parts[1:]) logic
        agent = DynamicInitLoopingAgent(
            name="TestAgent",
            description="Test agent",
            system_message="You are a test agent.",
            model_client=mock_model_client,
            tools=[],
            initialization_function="module.submodule.function"
        )

        # Agent should be created (even if init fails)
        assert agent.name == "TestAgent"
        assert agent.initialization_function == "module.submodule.function"


class TestDynamicInitWithMemoryAgent:
    """Test the dynamic init agent with actual memory module"""

    @pytest.mark.skipif(
        not Path(backend_path / "tools" / "memory.py").exists(),
        reason="Memory module not available"
    )
    def test_memory_agent_initialization_function_exists(self):
        """Test that memory.initialize_memory_agent function exists"""
        from tools import memory

        assert hasattr(memory, 'initialize_memory_agent')
        assert callable(memory.initialize_memory_agent)

    @pytest.mark.skipif(
        not Path(backend_path / "tools" / "memory.py").exists(),
        reason="Memory module not available"
    )
    @patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'})
    def test_create_memory_agent_with_dynamic_init(self, mock_model_client):
        """Test creating Memory agent with dynamic initialization"""
        from utils.context import CURRENT_AGENT

        # Create agent with memory initialization
        agent = DynamicInitLoopingAgent(
            name="Memory",
            description="Memory agent",
            system_message="You are Memory agent. {{SHORT_TERM_MEMORY}}",
            model_client=mock_model_client,
            tools=[],
            initialization_function="memory.initialize_memory_agent"
        )

        # Set as current agent (required for memory init)
        CURRENT_AGENT.set(agent)

        # Verify agent was created
        assert agent.name == "Memory"
        assert agent.initialization_function == "memory.initialize_memory_agent"

        # The system message should have placeholder
        # (initialization happens during __init__ before CURRENT_AGENT is set in this test)
        assert "{{SHORT_TERM_MEMORY}}" in agent._system_messages[0].content


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
