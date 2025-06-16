#!/usr/bin/env python3
"""
Interactive CLI for SMUS Admin Agent with MCP integration.
"""

import asyncio
import sys
from dotenv import load_dotenv
from src.smus_admin_agent import SMUSAdminAgent

# Load environment variables
load_dotenv()

async def interactive_chat():
    """Run an interactive chat session with the agent."""
    
    print("🚀 Starting SMUS Admin Agent with MCP Integration")
    print("=" * 60)
    
    # Create the agent
    print("🔧 Initializing agent...")
    agent = SMUSAdminAgent()
    
    # Check MCP integration
    if hasattr(agent, 'server_params'):
        print("✅ MCP integration configured")
        # Try to connect to MCP server
        mcp_available = await agent._ensure_mcp_client()
        if mcp_available:
            print("✅ Connected to DataZone MCP server")
            tools = await agent.list_mcp_tools()
            print(f"📋 Available MCP tools: {len(tools)}")
            print("   Sample tools:", tools[:5] if len(tools) > 5 else tools)
        else:
            print("⚠️  MCP server connection failed - continuing without MCP")
    else:
        print("ℹ️  No MCP configuration found")
    
    print("\n💬 Chat with your agent! (type 'quit' to exit)")
    print("=" * 60)
    
    session_id = "terminal_session"
    
    try:
        while True:
            # Get user input
            user_input = input("\n🧑 You: ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'bye']:
                print("Goodbye! Thanks for using SMUS Admin Agent.")
                break
            
            if not user_input:
                continue
            
            try:
                # Stream the response
                print("🤖 Agent: ", end="", flush=True)
                
                async for chunk in agent.stream_response(user_input, session_id):
                    print(chunk, end='', flush=True)
                
                print()  # New line after response
                
            except Exception as e:
                print(f"\n❌ Error: {e}")
                if "authentication_error" in str(e):
                    print("💡 Tip: Check your ANTHROPIC_API_KEY in the .env file")
                elif "MCP" in str(e):
                    print("💡 Tip: Check your MCP server configuration")
    
    except KeyboardInterrupt:
        print("\n\n👋 Interrupted by user. Goodbye!")
    
    finally:
        # Clean up MCP resources silently
        if hasattr(agent, 'cleanup_mcp'):
            try:
                await agent.cleanup_mcp()
            except:
                # Ignore cleanup errors - they're usually harmless
                pass

def main():
    """Main entry point."""
    try:
        asyncio.run(interactive_chat())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
        sys.exit(0)

if __name__ == "__main__":
    main() 