#!/usr/bin/env python3
"""
Interactive CLI for SMUS Admin Agent with MCP integration.
"""

import asyncio
import sys
from dotenv import load_dotenv
from src.smus_admin_agent import SMUSAdminAgent
import pandas as pd
import re
from tqdm.asyncio import tqdm

DATASET_PATH = "/Users/jiayixin/Desktop/smus_test.csv"
df = pd.read_csv(DATASET_PATH)

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
        print("MCP integration configured")
        # Try to connect to MCP server
        mcp_available = await agent._ensure_mcp_client()
        if mcp_available:
            print("Connected to DataZone MCP server")
            tools = await agent.list_mcp_tools()
            print(f"Available MCP tools: {len(tools)}")
            print("   Sample tools:", tools[:5] if len(tools) > 5 else tools)
        else:
            print("⚠️  MCP server connection failed - continuing without MCP")
    else:
        print("No MCP configuration found")
    
    print("\n Chat with your agent! (type 'quit' to exit)")
    print("=" * 60)
    
    session_id = "terminal_session"
    
    try:
        for index in tqdm(range(len(df)), desc="Processing questions"):
            row = df.iloc[index]
            user_input = row["question"]
            tool = await agent.test_response(user_input, session_id)

            # Optional: Update dataframe
            df.at[index, "api_called"] = ''.join(word.capitalize() for word in tool.split('_'))
            # Break early for test
    
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
    # Save the updated DataFrame to a CSV file
    output_path = "/Users/jiayixin/Desktop/smus_test_results.csv"
    df.to_csv(output_path, index=False)
    print(f"✅ Results saved to: {output_path}")

def main():
    """Main entry point."""
    try:
        asyncio.run(interactive_chat())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
        sys.exit(0)

if __name__ == "__main__":
    main() 