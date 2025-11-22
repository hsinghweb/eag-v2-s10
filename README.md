# EAG V2 Session 10 - Custom Multi-Agent System

## Overview
This project implements a custom Multi-Agent System (MAS) architecture where specialized agents collaborate to solve complex tasks. The system is built on a "Blackboard" pattern where agents communicate through a shared state.

## Architecture
The system consists of the following agents:
- **Coordinator**: The central orchestrator that manages the agent loop.
- **Perception Agent**: Analyzes user queries and tool results to update the system's understanding (ERORLL).
- **Decision Agent**: Plans and replans the execution strategy based on perception and memory.
- **Executor Agent**: Safely executes the plan steps using MCP tools.
- **Retriever Agent**: Fetches relevant context from documents and the web.
- **Memory Agent**: Manages session history and long-term memory.

## Data Flow
1. **User Query** -> **Perception Agent** (Creates Snapshot)
2. **Coordinator** -> **Retriever Agent** (Fetches Context)
3. **Coordinator** -> **Decision Agent** (Creates Plan)
4. **Coordinator** -> **Executor Agent** (Executes Step)
5. **Executor Result** -> **Perception Agent** (Updates Snapshot)
6. **Coordinator** -> **Decision Agent** (Replans/Next Step)
7. Loop continues until the goal is achieved.

## Setup
1. Install `uv`: `pip install uv`
2. Install dependencies: `uv sync`
3. Set `GEMINI_API_KEY` in `.env`.
4. Run the agent: `uv run main.py`

## Dependencies
- `google-genai`: For LLM capabilities (Gemini 2.0 Flash).
- `mcp`: For Model Context Protocol integration.
- `pydantic`: For structured data validation.
