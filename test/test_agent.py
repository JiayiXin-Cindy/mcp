"""Tests for SMUS Admin Agent."""

import pytest
import asyncio
import os
from unittest.mock import Mock, AsyncMock, patch
from src.smus_admin_agent import SMUSAdminAgent, ChatSession, ConversationState
from langchain_core.messages import HumanMessage, AIMessage


class TestChatSession:
    """Test ChatSession functionality."""
    
    def test_chat_session_creation(self):
        """Test creating a new chat session."""
        session = ChatSession(session_id="test_session")
        assert session.session_id == "test_session"
        assert len(session.messages) == 0
        assert session.created_at is not None
        assert session.updated_at is not None
    
    def test_add_message(self):
        """Test adding messages to a session."""
        session = ChatSession(session_id="test_session")
        message = HumanMessage(content="Hello")
        
        session.add_message(message)
        
        assert len(session.messages) == 1
        assert session.messages[0] == message
    
    def test_get_recent_messages(self):
        """Test getting recent messages from a session."""
        session = ChatSession(session_id="test_session")
        
        # Add multiple messages
        for i in range(15):
            session.add_message(HumanMessage(content=f"Message {i}"))
        
        # Test default limit (10)
        recent = session.get_recent_messages()
        assert len(recent) == 10
        assert recent[0].content == "Message 5"  # Should start from message 5
        
        # Test custom limit
        recent = session.get_recent_messages(limit=5)
        assert len(recent) == 5
        assert recent[0].content == "Message 10"  # Should start from message 10


class TestConversationState:
    """Test ConversationState functionality."""
    
    def test_conversation_state_creation(self):
        """Test creating a conversation state."""
        state = ConversationState()
        assert len(state.messages) == 0
        assert state.user_input == ""
        assert state.response == ""
    
    def test_conversation_state_with_data(self):
        """Test creating a conversation state with data."""
        messages = [HumanMessage(content="Hello")]
        state = ConversationState(
            messages=messages,
            user_input="Test input",
            response="Test response"
        )
        assert len(state.messages) == 1
        assert state.user_input == "Test input"
        assert state.response == "Test response"


class TestSMUSAdminAgent:
    """Test SMUSAdminAgent functionality."""
    
    @patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test-key'})
    def test_agent_creation(self):
        """Test creating an agent instance."""
        agent = SMUSAdminAgent()
        assert agent.llm is not None
        assert agent.graph is not None
        assert len(agent.sessions) == 0
    
    @patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test-key'})
    def test_get_or_create_session(self):
        """Test session creation and retrieval."""
        agent = SMUSAdminAgent()
        
        # Create new session
        session = agent.get_or_create_session("test_session")
        assert session.session_id == "test_session"
        assert "test_session" in agent.sessions
        
        # Get existing session
        same_session = agent.get_or_create_session("test_session")
        assert same_session is session
    
    @patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test-key'})
    def test_get_session_history(self):
        """Test getting session history."""
        agent = SMUSAdminAgent()
        
        # Empty history
        history = agent.get_session_history("nonexistent")
        assert history == []
        
        # Create session with messages
        session = agent.get_or_create_session("test_session")
        session.add_message(HumanMessage(content="Hello"))
        session.add_message(AIMessage(content="Hi there!"))
        
        history = agent.get_session_history("test_session")
        assert len(history) == 2
        assert history[0]["type"] == "human"
        assert history[0]["content"] == "Hello"
        assert history[1]["type"] == "ai"
        assert history[1]["content"] == "Hi there!"
    
    @patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test-key'})
    def test_clear_session(self):
        """Test clearing a session."""
        agent = SMUSAdminAgent()
        
        # Create session
        agent.get_or_create_session("test_session")
        assert "test_session" in agent.sessions
        
        # Clear session
        result = agent.clear_session("test_session")
        assert result is True
        assert "test_session" not in agent.sessions
        
        # Try to clear non-existent session
        result = agent.clear_session("nonexistent")
        assert result is False
    
    @patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test-key'})
    def test_list_sessions(self):
        """Test listing sessions."""
        agent = SMUSAdminAgent()
        
        # No sessions initially
        sessions = agent.list_sessions()
        assert sessions == []
        
        # Create some sessions
        agent.get_or_create_session("session1")
        agent.get_or_create_session("session2")
        
        sessions = agent.list_sessions()
        assert len(sessions) == 2
        assert "session1" in sessions
        assert "session2" in sessions
    
    @patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test-key'})
    @patch('src.smus_admin_agent.agent.ChatAnthropic')
    async def test_stream_response_mock(self, mock_chat_anthropic):
        """Test streaming response with mocked LLM."""
        # Mock the streaming response
        mock_llm = AsyncMock()
        mock_llm.astream.return_value = AsyncMock()
        mock_llm.astream.return_value.__aiter__ = AsyncMock(return_value=iter([
            Mock(content="Hello "),
            Mock(content="there!"),
        ]))
        mock_chat_anthropic.return_value = mock_llm
        
        agent = SMUSAdminAgent()
        
        response_parts = []
        async for chunk in agent.stream_response("Hello", "test_session"):
            response_parts.append(chunk)
        
        full_response = "".join(response_parts)
        assert "Hello there!" == full_response
        
        # Check that session was created and message was added
        assert "test_session" in agent.sessions
        session = agent.sessions["test_session"]
        assert len(session.messages) >= 1  # At least the user message
    
    @patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test-key'})
    @patch('src.smus_admin_agent.agent.ChatAnthropic')
    async def test_get_response_mock(self, mock_chat_anthropic):
        """Test getting complete response with mocked LLM."""
        # Mock the streaming response
        mock_llm = AsyncMock()
        mock_llm.astream.return_value = AsyncMock()
        mock_llm.astream.return_value.__aiter__ = AsyncMock(return_value=iter([
            Mock(content="Complete "),
            Mock(content="response!"),
        ]))
        mock_chat_anthropic.return_value = mock_llm
        
        agent = SMUSAdminAgent()
        
        response = await agent.get_response("Test question", "test_session")
        assert response == "Complete response!"


@pytest.mark.asyncio
async def test_error_handling():
    """Test error handling in agent methods."""
    with patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test-key'}):
        with patch('src.smus_admin_agent.agent.ChatAnthropic') as mock_chat:
            # Mock an error in streaming
            mock_llm = AsyncMock()
            mock_llm.astream.side_effect = Exception("API Error")
            mock_chat.return_value = mock_llm
            
            agent = SMUSAdminAgent()
            
            response_parts = []
            async for chunk in agent.stream_response("Test", "test_session"):
                response_parts.append(chunk)
            
            full_response = "".join(response_parts)
            assert "Error:" in full_response


def test_config_validation():
    """Test that agent requires valid configuration."""
    with patch.dict(os.environ, {}, clear=True):
        # Should raise ValueError when no API key is set
        with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
            from src.smus_admin_agent.config import Config
            Config() 