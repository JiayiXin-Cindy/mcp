"""Command Line Interface for SMUS Admin Agent."""

import asyncio
import sys
from typing import Optional
import argparse
from datetime import datetime

from .agent import SMUSAdminAgent
from .config import config


class AgentCLI:
    """Command Line Interface for the SMUS Admin Agent."""
    
    def __init__(self):
        self.agent = SMUSAdminAgent()
        self.session_id = "cli_session"
    
    def print_welcome(self):
        """Print welcome message."""
        print("=" * 60)
        print("SMUS Admin Agent - Interactive Chat")
        print("=" * 60)
        print("Using Claude 4 Sonnet model with streaming responses")
        print("Type 'quit', 'exit', or 'bye' to end the conversation")
        print("Type 'history' to see conversation history")
        print("Type 'clear' to clear conversation history")
        print("Type 'help' for more commands")
        print("=" * 60)
        print()
    
    def print_help(self):
        """Print available commands."""
        print("\nAvailable Commands:")
        print("  - quit/exit/bye - Exit the chat")
        print("  - history - Show conversation history")
        print("  - clear - Clear conversation history")
        print("  - help - Show this help message")
        print("  - sessions - List all active sessions")
        print("  - switch <session_id> - Switch to a different session")
        print()
    
    def print_history(self):
        """Print conversation history."""
        history = self.agent.get_session_history(self.session_id)
        if not history:
            print("No conversation history yet.\n")
            return
        
        print(f"\nConversation History (Session: {self.session_id}):")
        print("-" * 50)
        
        for i, entry in enumerate(history, 1):
            timestamp = datetime.fromisoformat(entry['timestamp']).strftime("%H:%M:%S")
            if entry['type'] == 'human':
                print(f"[{timestamp}] You: {entry['content']}")
            else:
                print(f"[{timestamp}] Agent: {entry['content']}")
        print("-" * 50)
        print()
    
    def clear_history(self):
        """Clear conversation history."""
        self.agent.clear_session(self.session_id)
        print("Conversation history cleared.\n")
    
    def list_sessions(self):
        """List all active sessions."""
        sessions = self.agent.list_sessions()
        if not sessions:
            print("No active sessions.\n")
            return
        
        print("\nActive Sessions:")
        for session in sessions:
            marker = ">" if session == self.session_id else " "
            print(f"{marker} {session}")
        print()
    
    def switch_session(self, session_id: str):
        """Switch to a different session."""
        self.session_id = session_id
        print(f"Switched to session: {session_id}\n")
    
    async def stream_chat_response(self, user_input: str):
        """Stream the agent's response."""
        print("Agent: ", end="", flush=True)
        
        try:
            async for chunk in self.agent.stream_response(user_input, self.session_id):
                print(chunk, end="", flush=True)
            print("\n")  # New line after streaming is complete
        except Exception as e:
            print(f"\nError: {str(e)}\n")
    
    async def run_interactive(self):
        """Run the interactive chat loop."""
        self.print_welcome()
        
        while True:
            try:
                # Get user input
                user_input = input("You: ").strip()
                
                if not user_input:
                    continue
                
                # Handle special commands
                if user_input.lower() in ['quit', 'exit', 'bye']:
                    print("Goodbye! Thanks for using SMUS Admin Agent.")
                    break
                
                elif user_input.lower() == 'help':
                    self.print_help()
                    continue
                
                elif user_input.lower() == 'history':
                    self.print_history()
                    continue
                
                elif user_input.lower() == 'clear':
                    self.clear_history()
                    continue
                
                elif user_input.lower() == 'sessions':
                    self.list_sessions()
                    continue
                
                elif user_input.lower().startswith('switch '):
                    session_id = user_input[7:].strip()
                    if session_id:
                        self.switch_session(session_id)
                    else:
                        print("Please provide a session ID. Usage: switch <session_id>\n")
                    continue
                
                # Process the user input with the agent
                await self.stream_chat_response(user_input)
                
            except KeyboardInterrupt:
                print("\n\nGoodbye! Thanks for using SMUS Admin Agent.")
                break
            except EOFError:
                print("\n\nGoodbye! Thanks for using SMUS Admin Agent.")
                break
            except Exception as e:
                print(f"\nUnexpected error: {str(e)}\n")


def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        description="SMUS Admin Agent - AI-powered admin assistant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  smus-admin-agent                    # Start interactive chat
  smus-admin-agent --session mysession  # Use specific session
        """
    )
    
    parser.add_argument(
        "--session",
        type=str,
        default="cli_session",
        help="Session ID to use for conversation history"
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version="SMUS Admin Agent 1.0"
    )
    
    args = parser.parse_args()
    
    # Check if configuration is valid
    try:
        if not config.is_configured:
            print("Configuration Error: ANTHROPIC_API_KEY is not set.")
            print("Please set your Anthropic API key in the environment:")
            print("  export ANTHROPIC_API_KEY='your_api_key_here'")
            print("Or create a .env file with:")
            print("  ANTHROPIC_API_KEY=your_api_key_here")
            sys.exit(1)
    except Exception as e:
        print(f"Configuration Error: {str(e)}")
        sys.exit(1)
    
    # Create and run the CLI
    cli = AgentCLI()
    cli.session_id = args.session
    
    try:
        asyncio.run(cli.run_interactive())
    except KeyboardInterrupt:
        print("\nGoodbye!")
    except Exception as e:
        print(f"Fatal error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main() 