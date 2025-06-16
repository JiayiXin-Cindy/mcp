#!/usr/bin/env python3
"""
Setup validation script for SMUS Admin Agent with MCP integration.
This script helps users verify their configuration is correct.
"""

import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

def print_status(message: str, status: str = "INFO"):
    """Print formatted status message."""
    symbols = {
        "SUCCESS": "✅",
        "ERROR": "❌", 
        "WARNING": "⚠️",
        "INFO": "ℹ️"
    }
    print(f"{symbols.get(status, 'ℹ️')} {message}")

def check_python_version():
    """Check if Python version is compatible."""
    version = sys.version_info
    if version.major == 3 and version.minor >= 8:
        print_status(f"Python version {version.major}.{version.minor}.{version.micro} is compatible", "SUCCESS")
        return True
    else:
        print_status(f"Python version {version.major}.{version.minor}.{version.micro} is not compatible. Required: Python 3.8+", "ERROR")
        return False

def check_environment_file():
    """Check if .env file exists and has required variables."""
    env_path = Path(".env")
    if not env_path.exists():
        print_status(".env file not found", "ERROR")
        print_status("Create a .env file based on env.example", "INFO")
        return False
    
    print_status(".env file found", "SUCCESS")
    
    # Load and check environment variables
    load_dotenv()
    
    required_vars = ["ANTHROPIC_API_KEY"]
    optional_vars = ["MCP_SERVER_PATH", "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"]
    
    missing_required = []
    for var in required_vars:
        if not os.getenv(var):
            missing_required.append(var)
    
    if missing_required:
        print_status(f"Missing required environment variables: {', '.join(missing_required)}", "ERROR")
        return False
    else:
        print_status("All required environment variables are set", "SUCCESS")
    
    # Check optional MCP variables
    mcp_path = os.getenv("MCP_SERVER_PATH")
    if mcp_path:
        print_status(f"MCP_SERVER_PATH is set to: {mcp_path}", "SUCCESS")
        if Path(mcp_path).exists():
            print_status("MCP server path exists", "SUCCESS")
        else:
            print_status("MCP server path does not exist", "WARNING")
            print_status("Make sure to install and set up your MCP server first", "INFO")
    else:
        print_status("MCP_SERVER_PATH not set - MCP integration will be disabled", "WARNING")
    
    return True

def check_dependencies():
    """Check if required packages are installed."""
    required_packages = [
        ("langchain", "langchain"),
        ("langchain_anthropic", "langchain-anthropic"),  
        ("langgraph", "langgraph"),
        ("anthropic", "anthropic"),
        ("dotenv", "python-dotenv"),
        ("pydantic", "pydantic"),
        ("mcp", "mcp")
    ]
    
    missing_packages = []
    
    for import_name, package_name in required_packages:
        try:
            __import__(import_name)
            print_status(f"Package '{package_name}' is installed", "SUCCESS")
        except ImportError:
            missing_packages.append(package_name)
            print_status(f"Package '{package_name}' is NOT installed", "ERROR")
    
    if missing_packages:
        print_status(f"Install missing packages with: pip install {' '.join(missing_packages)}", "INFO")
        return False
    
    return True

async def test_agent_creation():
    """Test if the agent can be created successfully."""
    try:
        from src.smus_admin_agent import SMUSAdminAgent
        
        print_status("Creating SMUS Admin Agent...", "INFO")
        agent = SMUSAdminAgent()
        print_status("Agent created successfully", "SUCCESS")
        
        # Test basic configuration
        if hasattr(agent, 'config') and agent.config.is_configured:
            print_status("Agent configuration is valid", "SUCCESS")
        else:
            print_status("Agent configuration has issues", "WARNING")
        
        # Test MCP configuration if available
        if hasattr(agent, 'config') and agent.config.is_mcp_configured:
            print_status("MCP configuration detected", "SUCCESS")
            
            # Try to connect to MCP server
            try:
                mcp_available = await agent._ensure_mcp_client()
                if mcp_available:
                    print_status("MCP server connection successful", "SUCCESS")
                    
                    # List available tools
                    tools = await agent.list_mcp_tools()
                    print_status(f"Found {len(tools)} MCP tools available", "SUCCESS")
                    if tools:
                        print_status(f"Sample tools: {', '.join(tools[:3])}", "INFO")
                else:
                    print_status("MCP server connection failed", "ERROR")
            except Exception as e:
                print_status(f"MCP connection error: {str(e)}", "ERROR")
            finally:
                # Clean up MCP resources silently
                if hasattr(agent, 'cleanup_mcp'):
                    try:
                        await agent.cleanup_mcp()
                    except:
                        # Ignore cleanup errors - they're usually harmless asyncio issues
                        pass
        else:
            print_status("MCP not configured - agent will work without MCP tools", "INFO")
        
        return True
        
    except ImportError as e:
        print_status(f"Cannot import agent: {str(e)}", "ERROR")
        print_status("Make sure you've installed the package with: pip install -e .", "INFO")
        return False
    except Exception as e:
        print_status(f"Error creating agent: {str(e)}", "ERROR")
        return False

async def run_validation():
    """Run all validation checks."""
    print("🚀 SMUS Admin Agent Setup Validation")
    print("=" * 50)
    
    checks_passed = 0
    total_checks = 4
    
    # Check 1: Python version
    print("\n1. Checking Python version...")
    if check_python_version():
        checks_passed += 1
    
    # Check 2: Environment file
    print("\n2. Checking environment configuration...")
    if check_environment_file():
        checks_passed += 1
    
    # Check 3: Dependencies
    print("\n3. Checking package dependencies...")
    if check_dependencies():
        checks_passed += 1
    
    # Check 4: Agent creation
    print("\n4. Testing agent creation...")
    if await test_agent_creation():
        checks_passed += 1
    
    # Summary
    print("\n" + "=" * 50)
    print(f"📊 Validation Summary: {checks_passed}/{total_checks} checks passed")
    
    if checks_passed == total_checks:
        print_status("🎉 All checks passed! Your setup is ready to use.", "SUCCESS")
        print_status("You can now run: python run_agent.py", "INFO")
    elif checks_passed >= 2:
        print_status("⚠️ Some issues found, but basic functionality should work", "WARNING")
        print_status("Review the errors above and fix them for full functionality", "INFO")
    else:
        print_status("❌ Multiple issues found. Please fix the errors above.", "ERROR")
        print_status("Refer to README.md for setup instructions", "INFO")

if __name__ == "__main__":
    try:
        asyncio.run(run_validation())
    except KeyboardInterrupt:
        print("\n\n🛑 Validation interrupted by user")
    except Exception as e:
        print(f"\n\n💥 Unexpected error during validation: {str(e)}")
        sys.exit(1) 