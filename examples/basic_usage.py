"""
Basic usage example for SMUS Admin Agent.

This example shows how to use the agent programmatically.
"""

import asyncio
import os
from src.smus_admin_agent import SMUSAdminAgent


async def main():
    """Main example function."""
    # Make sure to set your API key
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("Please set ANTHROPIC_API_KEY environment variable")
        return
    
    # Create the agent
    agent = SMUSAdminAgent()
    
    print("SMUS Admin Agent Example")
    print("=" * 40)
    
    # Example 1: Basic question
    print("\nExample 1: Basic question")
    user_input = "What is machine learning?"
    
    print(f"Question: {user_input}")
    print("Agent: ", end="", flush=True)
    
    async for chunk in agent.stream_response(user_input, session_id="example_session"):
        print(chunk, end="", flush=True)
    print("\n")
    
    # Example 2: Follow-up question (using conversation history)
    print("\nExample 2: Follow-up question")
    follow_up = "Can you give me a simple example?"
    
    print(f"Follow-up: {follow_up}")
    print("Agent: ", end="", flush=True)
    
    async for chunk in agent.stream_response(follow_up, session_id="example_session"):
        print(chunk, end="", flush=True)
    print("\n")
    
    # Example 3: Show conversation history
    print("\nConversation History:")
    history = agent.get_session_history("example_session")
    for i, entry in enumerate(history, 1):
        if entry['type'] == 'human':
            print(f"{i}. You: {entry['content']}")
        else:
            print(f"{i}. Agent: {entry['content'][:100]}..." if len(entry['content']) > 100 else f"{i}. Agent: {entry['content']}")
    
    print("\nExample completed!")


if __name__ == "__main__":
    asyncio.run(main()) 