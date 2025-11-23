#!/usr/bin/env python3
"""
Test to verify if MCP subprocess has access to tavily-python library
"""
import sys
import os

print(f"Python executable: {sys.executable}", file=sys.stderr)
print(f"Python version: {sys.version}", file=sys.stderr)
print(f"Current directory: {os.getcwd()}", file=sys.stderr)
print(f"sys.path: {sys.path[:3]}", file=sys.stderr)

try:
    from tavily import TavilyClient
    print("✅ tavily-python is available!", file=sys.stderr)
except ImportError as e:
    print(f"❌ tavily-python NOT available: {e}", file=sys.stderr)

try:
    from dotenv import load_dotenv
    print("✅ python-dotenv is available!", file=sys.stderr)
    
    # Try to load .env
    from pathlib import Path
    env_path = Path(__file__).parent.parent / ".env"
    load_dotenv(dotenv_path=env_path)
    
    api_key = os.getenv("TAVILY_API_KEY")
    if api_key:
        print(f"✅ TAVILY_API_KEY loaded: {api_key[:10]}...", file=sys.stderr)
    else:
        print("❌ TAVILY_API_KEY not found in environment", file=sys.stderr)
        
except ImportError as e:
    print(f"❌ python-dotenv NOT available: {e}", file=sys.stderr)

sys.stderr.flush()
