# SMUS Data Agent

A LangGraph-based AI agent powered by Anthropic's Claude 4 Sonnet model for data-related queries and conversations.

## Features

- **LangGraph Integration**: Built with LangGraph for flexible conversation flows
- **Streaming Responses**: Real-time streaming of AI responses
- **Conversation History**: Maintains context across conversations
- **CLI Interface**: Interactive terminal-based chat
- **API Ready**: Designed for integration with VS Code extensions
- **Session Management**: Support for multiple conversation sessions

## Quick Start

### Prerequisites

- Python 3.8 or higher
- pip (Python package installer)
- Git (for cloning repositories)

### Setup Checklist

Follow these steps to get your SMUS Data Agent up and running:

- [ ] **Clone and install the project**
- [ ] **Set up your `.env` file with API keys**  
- [ ] **Install MCP server (optional)**
- [ ] **Run validation script**
- [ ] **Test the agent**

### 1. Installation

```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e .

# Or install with development tools
pip install -e ".[dev]"
```

### 2. Set up API Key

Set your Anthropic API key as an environment variable:

```bash
export ANTHROPIC_API_KEY="your_api_key_here"
```

Or create a `.env` file in the project root:

```env
ANTHROPIC_API_KEY=your_api_key_here
DEFAULT_MODEL=claude-3-5-sonnet-20241022
MAX_TOKENS=4096
TEMPERATURE=0.7
```

## MCP Server Configuration

The SMUS Data Agent supports MCP (Model Context Protocol) servers to extend functionality with external tools and data sources. Currently, it's configured to work with AWS DataZone MCP server, but can be extended to support multiple MCP servers.

### How MCP Connection Works

The MCP server connection uses **STDIO communication** and is configured through environment variables:

1. **Configuration**: Set via `MCP_SERVER_PATH` in your `.env` file
2. **Connection**: Establishes STDIO communication with the MCP server process
3. **Tool Integration**: Automatically converts MCP tools to LangChain tools
4. **Lazy Loading**: Connects to MCP server only when needed

### Single MCP Server Setup

Add to your `.env` file:

```env
# MCP Server Configuration
MCP_SERVER_PATH=/path/to/your/mcp-server

# AWS Configuration (for DataZone MCP server)
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_DEFAULT_REGION=us-east-1
```

**Example for AWS DataZone MCP Server:**
```env
MCP_SERVER_PATH=/Volumes/workplace/amazon-datazone-mcp-server
```

### Multiple MCP Servers Setup

To connect multiple MCP servers, you'll need to modify the configuration. Here are two approaches:

#### Option 1: Additional Environment Variables
```env
# First MCP server (existing)
MCP_SERVER_PATH=/Volumes/workplace/amazon-datazone-mcp-server

# Second MCP server
MCP_SERVER_PATH_2=/path/to/your/second-mcp-server
MCP_SERVER_MODULE_2=your_second_server_module.server
```

#### Option 2: JSON Configuration (Recommended)
```env
MCP_SERVERS_CONFIG='[
  {
    "name": "datazone",
    "path": "/Volumes/workplace/amazon-datazone-mcp-server",
    "module": "datazone_mcp_server.server"
  },
  {
    "name": "your_second_server",
    "path": "/path/to/your/second-server",
    "module": "your_server.server"
  }
]'
```

### MCP Server Requirements

For an MCP server to work with this agent:

1. **Python Module**: Must be runnable as `python -m your_module.server`
2. **STDIO Protocol**: Must support MCP STDIO communication
3. **Virtual Environment**: Optional but recommended (agent will auto-detect `.venv/bin/python`)
4. **Tool Implementation**: Must implement MCP tool interface

### Testing MCP Connection

#### Quick Setup Validation

We've provided a comprehensive validation script to help you verify your setup:

```bash
# Run the setup validation script
python validate_setup.py
```

This script will check:
- ✅ Python version compatibility
- ✅ Environment file and required variables
- ✅ Package dependencies installation
- ✅ Agent creation and MCP connection

#### Manual Testing

You can also test individual components:

```bash
# Run the detailed MCP integration test
python test_mcp_integration.py

# Or run the agent interactively
python run_agent.py
```

### Code Changes for Multiple Servers

To add support for multiple MCP servers, you'll need to modify:

**1. Update `src/smus_data_agent/config.py`:**
```python
import json
from typing import List, Dict

class Config:
    def __init__(self):
        # ... existing code ...
        
        # Parse multiple MCP servers
        servers_config = os.getenv("MCP_SERVERS_CONFIG")
        if servers_config:
            try:
                self.mcp_servers = json.loads(servers_config)
            except json.JSONDecodeError:
                self.mcp_servers = []
        else:
            # Fallback to single server config
            if self.mcp_server_path:
                self.mcp_servers = [{
                    "name": "default",
                    "path": self.mcp_server_path,
                    "module": "datazone_mcp_server.server"
                }]
            else:
                self.mcp_servers = []
```

**2. Update `src/smus_data_agent/agent.py`:**
```python
class SMUSDataAgent:
    def __init__(self):
        # ... existing code ...
        self.mcp_clients: Dict[str, Any] = {}  # Multiple clients
        self.mcp_tools = []
        
        if config.mcp_servers and ClientSession:
            self._initialize_mcp_clients()
    
    def _initialize_mcp_clients(self):
        """Initialize multiple MCP clients."""
        self.server_params = {}
        
        for server_config in config.mcp_servers:
            name = server_config["name"]
            path = server_config["path"]
            module = server_config["module"]
            
            if not os.path.exists(path):
                print(f"⚠️ MCP server path does not exist: {path}")
                continue
            
            # Set up server parameters for each server
            server_venv_python = os.path.join(path, ".venv", "bin", "python")
            python_cmd = server_venv_python if os.path.exists(server_venv_python) else "python"
            
            self.server_params[name] = StdioServerParameters(
                command=python_cmd,
                args=["-m", module],
                env=None,
                cwd=path
            )
            print(f"✅ MCP server '{name}' parameters set up successfully!")
```

### Troubleshooting MCP Connection

Common issues and solutions:

1. **Server Path Not Found**: Ensure `MCP_SERVER_PATH` points to the correct directory
2. **Module Import Error**: Verify the server module is installed and importable
3. **Permission Issues**: Check that the Python executable has proper permissions
4. **Virtual Environment**: Agent will auto-detect `.venv/bin/python` in the server directory
5. **AWS Credentials**: For DataZone server, ensure AWS credentials are properly configured

### Current MCP Integration

The agent currently integrates with:
- **AWS DataZone MCP Server**: For data catalog and domain management
- Tools are automatically discovered and bound to the LLM
- Supports streaming responses with tool execution
- Handles tool errors gracefully

### 3. Validate Your Setup

Before running the agent, validate that everything is configured correctly:

```bash
# Run the comprehensive validation script
python validate_setup.py
```

This will check your Python version, environment variables, dependencies, and MCP connection. Fix any issues it reports before proceeding.

### 4. Run the Agent

#### Interactive CLI
```bash
# Start interactive chat
smus-data-agent

# Use a specific session
smus-data-agent --session my_session
```

#### Programmatic Usage
```python
import asyncio
from smus_data_agent import SMUSDataAgent

async def main():
    agent = SMUSDataAgent()
    
    # Stream response
    async for chunk in agent.stream_response("What is machine learning?"):
        print(chunk, end="", flush=True)

asyncio.run(main())
```

## CLI Commands

When using the interactive CLI, you have access to these commands:

- `quit`, `exit`, `bye` - Exit the chat
- `history` - Show conversation history
- `clear` - Clear conversation history
- `help` - Show available commands
- `sessions` - List all active sessions
- `switch <session_id>` - Switch to a different session

## Architecture

The agent is built using:

- **LangGraph**: For conversation flow management
- **Anthropic Claude 4 Sonnet**: As the language model
- **Streaming**: Real-time response generation
- **Session Management**: Persistent conversation contexts

## Integration with VS Code Extension

This agent is designed to be consumed by the SMUS Data Agent VS Code extension. The agent provides:

- Async streaming API for real-time responses
- Session management for persistent conversations
- JSON-serializable conversation history
- Error handling and graceful degradation

## First-Time Setup Guide

### Complete Setup from Scratch

If you're setting this up for the first time, follow these detailed steps:

#### Step 1: Clone and Install
```bash
# Clone the repository
git clone <repository-url>
cd SMUS-data-agent

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install the package
pip install -e .
```

#### Step 2: Create Environment File
```bash
# Copy the example environment file
cp env.example .env

# Edit the .env file with your actual values
# At minimum, you MUST set:
# - ANTHROPIC_API_KEY=your_actual_key_here
```

#### Step 3: Optional MCP Server Setup
```bash
# If you want to use AWS DataZone MCP server:
# 1. Clone the MCP server repository
git clone https://github.com/aws-samples/amazon-datazone-mcp-server.git
cd amazon-datazone-mcp-server

# 2. Install the MCP server
python -m venv .venv
source .venv/bin/activate
pip install -e .

# 3. Update your .env file with the correct path
# MCP_SERVER_PATH=/full/path/to/amazon-datazone-mcp-server

# 4. Set up AWS credentials in .env file
# AWS_ACCESS_KEY_ID=your_aws_key
# AWS_SECRET_ACCESS_KEY=your_aws_secret
# AWS_DEFAULT_REGION=us-east-1
```

#### Step 4: Validate Your Setup
```bash
# Back in the SMUS-data-agent directory
cd /path/to/SMUS-data-agent
source venv/bin/activate

# Run validation
python validate_setup.py
```

#### Step 5: Test the Agent
```bash
# If validation passed, run the agent
python run_agent.py
```

### Quick Troubleshooting

**"ANTHROPIC_API_KEY environment variable is required"**
- Make sure you created a `.env` file and set `ANTHROPIC_API_KEY=your_actual_key`
- Get your API key from: https://console.anthropic.com/

**"MCP server path does not exist"**
- Either install an MCP server or comment out `MCP_SERVER_PATH` in your `.env` file
- The agent works fine without MCP - you'll just have fewer tools available

**"Package X is NOT installed"**
- Run `pip install -e .` again in your activated virtual environment
- Make sure you're in the correct directory

**"Cannot import agent"**
- Make sure you've installed with `pip install -e .`
- Ensure you're in the project root directory

## Development

See instructions in DEVELOPMENT.md

## Documentation

Generated documentation for the latest released version can be accessed here:
https://devcentral.amazon.com/ac/brazil/package-master/package/go/documentation?name=SMUS-data-agent&interface=1.0&versionSet=live
