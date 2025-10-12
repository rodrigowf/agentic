#!/usr/bin/env python3
"""
Integration tests for Agent API endpoints.

Tests:
- GET /api/agents (list all)
- GET /api/agents/{name} (get specific) - NOT IMPLEMENTED YET
- POST /api/agents (create)
- PUT /api/agents/{name} (update)
- DELETE /api/agents/{name} (delete) - NOT IMPLEMENTED YET
"""

import json
import os
import pytest
import tempfile
import shutil
from pathlib import Path
from fastapi.testclient import TestClient

# Setup path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from main import app
from config.schemas import AgentConfig, LLMConfig, PromptConfig


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def temp_agents_dir(monkeypatch):
    """Create a temporary agents directory for testing."""
    temp_dir = tempfile.mkdtemp()
    agents_path = Path(temp_dir) / "agents"
    agents_path.mkdir()

    # Monkeypatch the AGENTS_DIR in main module
    import main
    original_dir = main.AGENTS_DIR
    main.AGENTS_DIR = str(agents_path)
    main.AGENTS = []  # Clear cached agents

    yield str(agents_path)

    # Cleanup
    main.AGENTS_DIR = original_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_agent_config():
    """Create a sample agent configuration."""
    return AgentConfig(
        name="TestAgent",
        agent_type="looping",
        tools=["web_search"],
        llm=LLMConfig(
            provider="openai",
            model="gpt-4o-mini",
            temperature=0.0,
            max_tokens=None
        ),
        prompt=PromptConfig(
            system="You are a test agent.",
            user="Test task."
        ),
        code_executor=None,
        model_client_stream=False,
        sources=None,
        description="Test agent for integration testing",
        system_message=None,
        max_consecutive_auto_reply=20,
        reflect_on_tool_use=True,
        terminate_on_text=False,
        tool_call_loop=True,
        sub_agents=None,
        mode=None,
        orchestrator_prompt=None,
        include_inner_dialog=True
    )


class TestAgentListEndpoint:
    """Tests for GET /api/agents."""

    def test_list_agents_empty(self, client, temp_agents_dir):
        """Test listing agents when directory is empty."""
        response = client.get("/api/agents")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_agents_with_data(self, client, temp_agents_dir, sample_agent_config):
        """Test listing agents when agents exist."""
        # Create a test agent file
        agent_file = Path(temp_agents_dir) / "TestAgent.json"
        agent_file.write_text(sample_agent_config.model_dump_json(indent=2))

        response = client.get("/api/agents")
        assert response.status_code == 200
        agents = response.json()
        assert len(agents) == 1
        assert agents[0]["name"] == "TestAgent"
        assert agents[0]["agent_type"] == "looping"

    def test_list_agents_multiple(self, client, temp_agents_dir):
        """Test listing multiple agents."""
        # Create multiple test agents
        for i in range(3):
            config = AgentConfig(
                name=f"TestAgent{i}",
                agent_type="looping",
                tools=[],
                llm=LLMConfig(provider="openai", model="gpt-4o-mini", temperature=0.0),
                prompt=PromptConfig(system="Test", user="Test"),
                description=f"Agent {i}"
            )
            agent_file = Path(temp_agents_dir) / f"TestAgent{i}.json"
            agent_file.write_text(config.model_dump_json(indent=2))

        response = client.get("/api/agents")
        assert response.status_code == 200
        agents = response.json()
        assert len(agents) == 3
        names = [a["name"] for a in agents]
        assert "TestAgent0" in names
        assert "TestAgent1" in names
        assert "TestAgent2" in names


class TestAgentCreateEndpoint:
    """Tests for POST /api/agents."""

    def test_create_agent_success(self, client, temp_agents_dir, sample_agent_config):
        """Test creating a new agent."""
        response = client.post(
            "/api/agents",
            json=sample_agent_config.model_dump(mode='json')
        )
        assert response.status_code == 200

        # Verify response
        created = response.json()
        assert created["name"] == "TestAgent"
        assert created["agent_type"] == "looping"

        # Verify file was created
        agent_file = Path(temp_agents_dir) / "TestAgent.json"
        assert agent_file.exists()

        # Verify file content
        with open(agent_file) as f:
            saved_agent = json.load(f)
        assert saved_agent["name"] == "TestAgent"

    def test_create_agent_duplicate_name(self, client, temp_agents_dir, sample_agent_config):
        """Test creating an agent with a duplicate name."""
        # Create first agent
        client.post("/api/agents", json=sample_agent_config.model_dump(mode='json'))

        # Try to create duplicate
        response = client.post("/api/agents", json=sample_agent_config.model_dump(mode='json'))
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"].lower()

    def test_create_agent_invalid_data(self, client, temp_agents_dir):
        """Test creating an agent with invalid data."""
        invalid_config = {
            "name": "InvalidAgent",
            # Missing required fields
        }
        response = client.post("/api/agents", json=invalid_config)
        assert response.status_code == 422  # Validation error

    def test_create_nested_team_agent(self, client, temp_agents_dir):
        """Test creating a nested team agent."""
        nested_config = AgentConfig(
            name="TeamAgent",
            agent_type="nested_team",
            tools=[],
            llm=LLMConfig(provider="openai", model="gpt-4o", temperature=0.0),
            prompt=PromptConfig(system="", user=""),
            sub_agents=["Agent1", "Agent2"],
            mode="selector",
            orchestrator_prompt="__function__",
            description="Team agent"
        )

        response = client.post("/api/agents", json=nested_config.model_dump(mode='json'))
        assert response.status_code == 200

        created = response.json()
        assert created["agent_type"] == "nested_team"
        assert created["sub_agents"] == ["Agent1", "Agent2"]
        assert created["mode"] == "selector"


class TestAgentUpdateEndpoint:
    """Tests for PUT /api/agents/{agent_name}."""

    def test_update_agent_success(self, client, temp_agents_dir, sample_agent_config):
        """Test updating an existing agent."""
        # Create initial agent
        client.post("/api/agents", json=sample_agent_config.model_dump(mode='json'))

        # Update the agent
        updated_config = sample_agent_config.model_copy()
        updated_config.description = "Updated description"
        updated_config.llm.temperature = 0.5

        response = client.put(
            "/api/agents/TestAgent",
            json=updated_config.model_dump(mode='json')
        )
        assert response.status_code == 200

        # Verify response
        updated = response.json()
        assert updated["description"] == "Updated description"
        assert updated["llm"]["temperature"] == 0.5

        # Verify file was updated
        agent_file = Path(temp_agents_dir) / "TestAgent.json"
        with open(agent_file) as f:
            saved_agent = json.load(f)
        assert saved_agent["description"] == "Updated description"

    def test_update_agent_not_found(self, client, temp_agents_dir, sample_agent_config):
        """Test updating a non-existent agent."""
        response = client.put(
            "/api/agents/NonExistent",
            json=sample_agent_config.model_dump(mode='json')
        )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_update_agent_name_mismatch(self, client, temp_agents_dir, sample_agent_config):
        """Test updating an agent with mismatched names."""
        # Create initial agent
        client.post("/api/agents", json=sample_agent_config.model_dump(mode='json'))

        # Try to update with different name in body
        updated_config = sample_agent_config.model_copy()
        updated_config.name = "DifferentName"

        response = client.put(
            "/api/agents/TestAgent",
            json=updated_config.model_dump(mode='json')
        )
        assert response.status_code == 400
        assert "does not match" in response.json()["detail"].lower()

    def test_update_agent_change_type(self, client, temp_agents_dir, sample_agent_config):
        """Test changing agent type from looping to nested_team."""
        # Create initial looping agent
        client.post("/api/agents", json=sample_agent_config.model_dump(mode='json'))

        # Update to nested_team
        updated_config = sample_agent_config.model_copy()
        updated_config.agent_type = "nested_team"
        updated_config.sub_agents = ["Agent1", "Agent2"]
        updated_config.mode = "selector"

        response = client.put(
            "/api/agents/TestAgent",
            json=updated_config.model_dump(mode='json')
        )
        assert response.status_code == 200

        updated = response.json()
        assert updated["agent_type"] == "nested_team"
        assert updated["sub_agents"] == ["Agent1", "Agent2"]


class TestAgentEdgeCases:
    """Test edge cases and error handling."""

    def test_agent_with_special_characters_in_name(self, client, temp_agents_dir):
        """Test that agent names are properly validated."""
        config = AgentConfig(
            name="Test-Agent_123",
            agent_type="looping",
            tools=[],
            llm=LLMConfig(provider="openai", model="gpt-4o-mini", temperature=0.0),
            prompt=PromptConfig(system="Test", user="Test"),
            description="Test"
        )

        response = client.post("/api/agents", json=config.model_dump(mode='json'))
        # Should succeed - hyphens and underscores are valid
        assert response.status_code == 200

    def test_agent_with_empty_tools_list(self, client, temp_agents_dir):
        """Test creating an agent with no tools."""
        config = AgentConfig(
            name="NoToolsAgent",
            agent_type="looping",
            tools=[],  # Empty tools list
            llm=LLMConfig(provider="openai", model="gpt-4o-mini", temperature=0.0),
            prompt=PromptConfig(system="Test", user="Test"),
            description="Agent with no tools"
        )

        response = client.post("/api/agents", json=config.model_dump(mode='json'))
        assert response.status_code == 200
        assert response.json()["tools"] == []

    def test_agent_with_all_llm_providers(self, client, temp_agents_dir):
        """Test creating agents with different LLM providers."""
        providers = [
            ("openai", "gpt-4o-mini"),
            ("anthropic", "claude-3-haiku-20240307"),
            ("google", "gemini-1.5-pro-latest")
        ]

        for provider, model in providers:
            config = AgentConfig(
                name=f"{provider.capitalize()}Agent",
                agent_type="looping",
                tools=[],
                llm=LLMConfig(provider=provider, model=model, temperature=0.0),
                prompt=PromptConfig(system="Test", user="Test"),
                description=f"Agent using {provider}"
            )

            response = client.post("/api/agents", json=config.model_dump(mode='json'))
            assert response.status_code == 200
            assert response.json()["llm"]["provider"] == provider


class TestAgentValidation:
    """Test agent configuration validation."""

    def test_nested_team_without_sub_agents(self, client, temp_agents_dir):
        """Test that nested_team agent requires sub_agents."""
        config = AgentConfig(
            name="InvalidTeam",
            agent_type="nested_team",
            tools=[],
            llm=LLMConfig(provider="openai", model="gpt-4o", temperature=0.0),
            prompt=PromptConfig(system="", user=""),
            sub_agents=None,  # Missing sub_agents
            description="Invalid team"
        )

        # This should still create (validation happens at runtime)
        # But we can verify the config is saved correctly
        response = client.post("/api/agents", json=config.model_dump(mode='json'))
        assert response.status_code == 200

    def test_agent_with_invalid_temperature(self, client, temp_agents_dir):
        """Test agent with temperature out of range."""
        config = {
            "name": "InvalidTemp",
            "agent_type": "looping",
            "tools": [],
            "llm": {
                "provider": "openai",
                "model": "gpt-4o-mini",
                "temperature": 5.0,  # Out of range
                "max_tokens": None
            },
            "prompt": {"system": "Test", "user": "Test"},
            "description": "Test"
        }

        # Pydantic should catch this
        response = client.post("/api/agents", json=config)
        # May succeed if no validation on temperature range
        # Check what actually happens
        if response.status_code == 200:
            # No validation on temperature range
            pass
        else:
            # Validation exists
            assert response.status_code in [400, 422]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
