#!/usr/bin/env python3
"""
Wrapper script to run the DataZone MCP server with the correct Python path.
"""
import os
import sys

# Add the src directory to the Python path
src_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src")
sys.path.insert(0, src_path)

# Now import and run the server
from datazone_mcp_server.server import main

if __name__ == "__main__":
    main()