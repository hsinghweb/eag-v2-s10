# EAG V2 Session 10 - Custom Multi-Agent System

## Overview
This project implements a custom Multi-Agent System (MAS) architecture where specialized agents collaborate to solve complex tasks. The system is built on a "Blackboard" pattern where agents communicate through a shared state. It now features a **Web Interface** for interactive chat and **Human-in-the-Loop (HITL)** controls for supervising agent actions.

## Architecture
The system consists of the following agents:
- **Coordinator**: The central orchestrator that manages the agent loop. It supports both CLI and Web interfaces via an abstract `IOHandler`.
- **Perception Agent**: Analyzes user queries and tool results to update the system's understanding (ERORLL).
- **Decision Agent**: Plans and replans the execution strategy based on perception and memory.
- **Executor Agent**: Safely executes the plan steps using MCP tools.
- **Retriever Agent**: Fetches relevant context from documents and the web.
- **Memory Agent**: Manages session history and long-term memory.

### Web Application Stack
- **Backend**: FastAPI with WebSockets for real-time communication.
- **Frontend**: Single-page application (HTML/JS/TailwindCSS) with a ChatGPT-like interface.
- **Communication**: Event-driven architecture where agent steps (Perception, Plan, Execution) are streamed to the UI.

## Data Flow
1. **User Query** -> **Perception Agent** (Creates Snapshot)
2. **Coordinator** -> **Retriever Agent** (Fetches Context)
3. **Coordinator** -> **Decision Agent** (Creates Plan)
4. **Coordinator** -> **Executor Agent** (Executes Step)
5. **Executor Result** -> **Perception Agent** (Updates Snapshot)
6. **Coordinator** -> **Decision Agent** (Replans/Next Step)
7. Loop continues until the goal is achieved.

## Human-in-the-Loop (HITL)
The system supports granular control over the agent's autonomy:
- **Plan Approval**: Review and approve/reject the agent's proposed plan before execution starts.
- **Step Approval**: Review each step's code and description before it runs.
- **Feedback Loop**: Provide feedback during approval to force the agent to replan or correct its course.

These features can be toggled dynamically from the Web UI sidebar.

## Setup

### Prerequisites
1. Install `uv`: `pip install uv`
2. Install dependencies: `uv sync`
3. Set `GEMINI_API_KEY` in `.env`.

### Running the Web Application (Recommended)
Start the FastAPI server with hot-reload:
```bash
uv run uvicorn server:app --reload
```
Open your browser and navigate to: `http://127.0.0.1:8000`

### Running the CLI (Legacy)
To run the agent in the command line:
```bash
uv run main.py
```

## Dependencies
- `google-genai`: For LLM capabilities (Gemini 2.0 Flash).
- `mcp`: For Model Context Protocol integration.
- `fastapi` & `uvicorn`: For the web server.
- `websockets`: For real-time client-server communication.
- `pydantic`: For structured data validation.
