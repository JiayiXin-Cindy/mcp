"""Main LangGraph agent implementation for SMUS Admin Agent."""

import asyncio
import os
import sys
from contextlib import AsyncExitStack
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, AsyncGenerator, Dict, List

from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langchain_core.tools import BaseTool
from langchain_anthropic import ChatAnthropic
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from pydantic import BaseModel, Field

from .config import config

try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
except ImportError:
    ClientSession = None
    StdioServerParameters = None
    stdio_client = None


class MCPTool(BaseTool):
    """A LangChain tool that wraps an MCP tool."""
    
    mcp_tool_name: str = Field(description="The name of the MCP tool")
    agent: Any = Field(description="Reference to the agent")
    
    def _run(self, **kwargs) -> str:
        """Synchronous run - not implemented for async tools."""
        raise NotImplementedError("This tool only supports async execution")
    
    async def _arun(self, **kwargs) -> str:
        """Execute the MCP tool asynchronously."""
        try:
            result = await self.agent.call_mcp_tool(self.mcp_tool_name, kwargs)
            # Convert result to string if it's not already
            if isinstance(result, list):
                # Handle list of content items
                content_parts = []
                for item in result:
                    if hasattr(item, 'text'):
                        content_parts.append(item.text)
                    elif isinstance(item, dict) and 'text' in item:
                        content_parts.append(item['text'])
                    else:
                        content_parts.append(str(item))
                return "\n".join(content_parts)
            elif hasattr(result, 'text'):
                return result.text
            elif isinstance(result, dict) and 'text' in result:
                return result['text']
            return str(result)
        except Exception as e:
            return f"Error calling {self.mcp_tool_name}: {str(e)}"


class ConversationState(BaseModel):
    """State for the conversation graph."""
    messages: List[BaseMessage] = field(default_factory=list)
    user_input: str = ""
    response: str = ""
    
    class Config:
        arbitrary_types_allowed = True


@dataclass
class ChatSession:
    """Represents a chat session with conversation history."""
    session_id: str
    messages: List[BaseMessage] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def add_message(self, message: BaseMessage):
        """Add a message to the session history."""
        self.messages.append(message)
        self.updated_at = datetime.now()
    
    def get_recent_messages(self, limit: int = 10) -> List[BaseMessage]:
        """Get recent messages from the session."""
        return self.messages[-limit:] if self.messages else []


class SMUSAdminAgent:
    """LangGraph-based AI agent for SMUS admin queries."""
    
    def __init__(self):
        self.config = config  # Store config as instance variable
        self.llm = ChatAnthropic(
            model=config.default_model,
            api_key=config.anthropic_api_key,
            max_tokens=config.max_tokens,
            temperature=config.temperature,
            streaming=True
        )
        self.graph = self._build_graph()
        self.sessions: Dict[str, ChatSession] = {}
        self.mcp_client = None
        self.exit_stack = None
        self.mcp_tools = []  # Store converted MCP tools
        if config.is_mcp_configured and ClientSession:
            self._initialize_mcp_client()
    
    def _initialize_mcp_client(self):
        """Initialize the MCP client."""
        try:
            # The mcp_server_path should point to the local server directory
            # We need to run: python -m datazone_mcp_server.server from that directory
            server_path = config.mcp_server_path
            if not os.path.exists(server_path):
                raise ValueError(f"MCP server path does not exist: {server_path}")
            
            print(f"🔍 Debug: Initializing MCP client with server path: {server_path}")
            
            # Check if there's a virtual environment in the server directory
            server_venv_python = os.path.join(server_path, ".venv", "bin", "python")
            if os.path.exists(server_venv_python):
                python_cmd = server_venv_python
                print(f"🔍 Debug: Using server's virtual environment: {python_cmd}")
            else:
                # Use system python and hope the package is installed globally
                python_cmd = "python"
                print(f"🔍 Debug: Using system python: {python_cmd}")
            
            # Create server parameters for stdio connection
            server_params = StdioServerParameters(
                command=python_cmd,
                args=["-m", "datazone_mcp_server.server"],
                env=None,
                cwd=server_path
            )
            
            print(f"🔍 Debug: Server params - command: {server_params.command}, args: {server_params.args}, cwd: {server_params.cwd}")
            
            # This is an async operation, but we are in a sync constructor.
            # For now, we'll set up the parameters and initialize later
            self.server_params = server_params
            print("✅ MCP client parameters set up successfully!")
        except Exception as e:
            print(f"Failed to set up MCP client: {e}")
            import traceback
            traceback.print_exc()
            self.mcp_client = None
    
    async def _ensure_mcp_client(self):
        """Ensure MCP client is connected (lazy initialization)."""
        if self.mcp_client is None and hasattr(self, 'server_params'):
            try:
                self.exit_stack = AsyncExitStack()
                stdio_transport = await self.exit_stack.enter_async_context(
                    stdio_client(self.server_params)
                )
                self.stdio, self.write = stdio_transport
                self.mcp_client = await self.exit_stack.enter_async_context(
                    ClientSession(self.stdio, self.write)
                )
                await self.mcp_client.initialize()
                print("✅ MCP client connected and initialized!")
                
                # Convert MCP tools to LangChain tools
                await self._setup_mcp_tools()
                return True
            except Exception as e:
                print(f"Failed to connect MCP client: {e}")
                import traceback
                traceback.print_exc()
                return False
        return self.mcp_client is not None
    
    async def _setup_mcp_tools(self):
        """Convert MCP tools to LangChain tools."""
        if not self.mcp_client:
            return
        
        try:
            # Get MCP tools
            tools_response = await self.mcp_client.list_tools()
            self.mcp_tools = []
            
            for mcp_tool in tools_response.tools:
                # Create a LangChain tool wrapper
                langchain_tool = MCPTool(
                    name=mcp_tool.name,
                    description=mcp_tool.description or f"MCP tool: {mcp_tool.name}",
                    mcp_tool_name=mcp_tool.name,
                    agent=self
                )
                self.mcp_tools.append(langchain_tool)
            
            # Bind tools to the LLM
            if self.mcp_tools:
                self.llm_with_tools = self.llm.bind_tools(self.mcp_tools)
                print(f"✅ Bound {len(self.mcp_tools)} MCP tools to LLM")
            else:
                self.llm_with_tools = self.llm
                
        except Exception as e:
            print(f"Failed to setup MCP tools: {e}")
            self.llm_with_tools = self.llm
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph conversation graph."""
        
        def chat_node(state: ConversationState) -> ConversationState:
            """Main chat node that processes user input and generates responses."""
            try:
                # Prepare messages for the LLM
                messages = state.messages.copy()
                if state.user_input:
                    messages.append(HumanMessage(content=state.user_input))
                
                # Generate response using the LLM
                response = self.llm.invoke(messages)
                
                # Update state
                state.messages = messages + [response]
                state.response = response.content
                
                return state
            
            except Exception as e:
                error_msg = f"Error processing request: {str(e)}"
                state.response = error_msg
                state.messages.append(AIMessage(content=error_msg))
                return state
        
        # Build the graph
        workflow = StateGraph(ConversationState)
        
        # Add nodes
        workflow.add_node("chat", chat_node)
        
        # Add edges
        workflow.add_edge(START, "chat")
        workflow.add_edge("chat", END)
        
        return workflow.compile()
    
    def get_or_create_session(self, session_id: str) -> ChatSession:
        """Get an existing session or create a new one."""
        if session_id not in self.sessions:
            self.sessions[session_id] = ChatSession(session_id=session_id)
        return self.sessions[session_id]
    
    async def stream_response(
        self, 
        user_input: str, 
        session_id: str = "default"
    ) -> AsyncGenerator[str, None]:
        """Stream the agent's response to user input with MCP tool support."""
        try:
            session = self.get_or_create_session(session_id)
            
            # Ensure MCP client is connected and tools are set up
            await self._ensure_mcp_client()
            
            # Add user message to session
            session.add_message(HumanMessage(content=user_input))
            
            # Prepare messages with conversation history
            messages = session.get_recent_messages() + [HumanMessage(content=user_input)]
            
            # Use LLM with tools if available, otherwise regular LLM
            llm_to_use = getattr(self, 'llm_with_tools', self.llm)
            
            response_content = ""
            
            # Stream response from LLM
            async for chunk in llm_to_use.astream(messages):
                # Check for tool calls first
                if hasattr(chunk, 'tool_calls') and chunk.tool_calls:
                    # Process each tool call
                    for tool_call in chunk.tool_calls:
                        if tool_call.get('name') and tool_call.get('name') != '':  # Skip empty tool calls
                            tool_name = tool_call['name']
                            tool_args = tool_call.get('args', {})
                            tool_id = tool_call.get('id', 'unknown')
                            
                            yield f"\n🔧 [Calling DataZone tool: {tool_name}]\n"
                            
                            try:
                                # Execute the MCP tool
                                result = await self.call_mcp_tool(tool_name, tool_args)
                                
                                # Format the result nicely
                                if isinstance(result, list) and len(result) == 0:
                                    formatted_result = "No results found."
                                elif isinstance(result, list):
                                    formatted_result = f"Found {len(result)} results:\n" + "\n".join([f"- {item}" for item in result[:10]])
                                    if len(result) > 10:
                                        formatted_result += f"\n... and {len(result) - 10} more"
                                else:
                                    formatted_result = str(result)
                                
                                yield f"✅ Tool result: {formatted_result}\n\n"
                                
                                # Add tool result to conversation context
                                messages.append(AIMessage(content=f"I called the {tool_name} tool."))
                                messages.append(HumanMessage(content=f"Tool {tool_name} returned: {formatted_result}"))
                                
                                # Get AI's interpretation of the result
                                async for final_chunk in self.llm.astream(messages):
                                    if hasattr(final_chunk, 'content') and final_chunk.content:
                                        # Handle different content formats
                                        if isinstance(final_chunk.content, str):
                                            content_text = final_chunk.content
                                        elif isinstance(final_chunk.content, list):
                                            content_parts = []
                                            for item in final_chunk.content:
                                                if isinstance(item, dict) and 'text' in item:
                                                    content_parts.append(item['text'])
                                                elif hasattr(item, 'text'):
                                                    content_parts.append(item.text)
                                                else:
                                                    content_parts.append(str(item))
                                            content_text = "".join(content_parts)
                                        else:
                                            content_text = str(final_chunk.content)
                                        
                                        response_content += content_text
                                        yield content_text
                                        
                            except Exception as e:
                                error_msg = f"Error executing tool {tool_name}: {str(e)}"
                                yield f"\n❌ {error_msg}\n"
                                response_content += error_msg
                
                elif hasattr(chunk, 'content') and chunk.content:
                    # Handle regular content
                    if isinstance(chunk.content, str):
                        content_text = chunk.content
                    elif isinstance(chunk.content, list):
                        # Extract text from list of content items
                        content_parts = []
                        for item in chunk.content:
                            if isinstance(item, dict) and 'text' in item:
                                content_parts.append(item['text'])
                            elif hasattr(item, 'text'):
                                content_parts.append(item.text)
                            else:
                                content_parts.append(str(item))
                        content_text = "".join(content_parts)
                    else:
                        content_text = str(chunk.content)
                    
                    response_content += content_text
                    yield content_text
            
            # Add AI response to session
            if response_content:
                session.add_message(AIMessage(content=response_content))
            
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            yield error_msg
    
    async def get_response(
        self, 
        user_input: str, 
        session_id: str = "default"
    ) -> str:
        """Get a complete response from the agent."""
        response_parts = []
        async for chunk in self.stream_response(user_input, session_id):
            response_parts.append(chunk)
        return "".join(response_parts)
    
    def get_session_history(self, session_id: str) -> List[Dict[str, Any]]:
        """Get the history of a session in a serializable format."""
        if session_id not in self.sessions:
            return []
        
        session = self.sessions[session_id]
        history = []
        
        for message in session.messages:
            if isinstance(message, HumanMessage):
                history.append({
                    "type": "human",
                    "content": message.content,
                    "timestamp": session.updated_at.isoformat()
                })
            elif isinstance(message, AIMessage):
                history.append({
                    "type": "ai",
                    "content": message.content,
                    "timestamp": session.updated_at.isoformat()
                })
        
        return history
    
    def clear_session(self, session_id: str) -> bool:
        """Clear a specific session."""
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False
    
    def list_sessions(self) -> List[str]:
        """List all active session IDs."""
        return list(self.sessions.keys())
    
    async def call_mcp_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Call an MCP tool if the client is available."""
        if not await self._ensure_mcp_client():
            raise ValueError("MCP client is not available")
        
        try:
            result = await self.mcp_client.call_tool(tool_name, arguments)
            # Return the raw content - let the MCPTool wrapper handle string conversion
            return result.content
        except Exception as e:
            raise ValueError(f"Failed to call MCP tool '{tool_name}': {str(e)}")
    
    async def list_mcp_tools(self) -> List[str]:
        """List available MCP tools."""
        if not await self._ensure_mcp_client():
            return []
        
        try:
            tools = await self.mcp_client.list_tools()
            return [tool.name for tool in tools.tools]
        except Exception as e:
            print(f"Failed to list MCP tools: {e}")
            return []

    async def cleanup_mcp(self):
        """Clean up MCP resources."""
        try:
            if self.exit_stack:
                # Set client to None first to prevent further use
                self.mcp_client = None
                # Then close the exit stack
                await self.exit_stack.aclose()
                self.exit_stack = None
        except Exception as e:
            # Suppress cleanup errors to avoid confusing users
            # These are usually harmless asyncio context manager issues
            pass 