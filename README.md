# EAG V2 Session 10 - Custom Multi-Agent System

## 🌟 Overview
This project implements a robust **Custom Multi-Agent System (MAS)** designed to solve complex tasks through collaboration between specialized agents. Built on a **Blackboard Architecture**, the system features a central shared state that allows agents to read and write context asynchronously.

The system is equipped with a **Tiered Memory System** (Session, Conversation, Document), **Human-in-the-Loop (HITL)** controls, and a modern **Web Interface** for interaction. It uses the **Model Context Protocol (MCP)** to integrate external tools and servers.

## 🏗️ Architecture

The system follows a modular architecture where a **Coordinator** orchestrates the workflow between specialized agents.

### Core Agents
*   **Coordinator**: The central brain that manages the control flow, initializes agents, and handles I/O.
*   **Perception Agent**: Analyzes user queries and tool outputs to update the system's understanding of the state.
*   **Decision Agent**: Responsible for planning, replanning, and determining the next logical step.
*   **Executor Agent**: Safely executes code and calls MCP tools based on the plan.
*   **Retriever Agent**: Fetches relevant context from long-term memory and local documents (RAG).
*   **Memory Agent**: Manages the tiered memory system, ensuring context is preserved across turns and sessions.

### Data Flow
1.  **User Query** → **Perception Agent** (Creates initial snapshot)
2.  **Coordinator** → **Retriever Agent** (Fetches relevant context)
3.  **Coordinator** → **Decision Agent** (Generates a plan)
4.  **Coordinator** → **Executor Agent** (Executes the first step)
5.  **Tool/Code Result** → **Perception Agent** (Updates state with result)
6.  **Coordinator** → **Decision Agent** (Replans based on new state)
7.  *Loop continues until the goal is achieved.*

## ✨ Key Features

### 🧠 Tiered Memory System
1.  **Tier 1: Session Memory**: Short-term context for the current active conversation.
2.  **Tier 2: Conversation Memory**: Long-term storage using FAISS vector database to recall facts from past conversations.
3.  **Tier 3: Document Memory**: RAG system for retrieving information from local documents.

### 🛡️ Human-in-the-Loop (HITL)
Granular control over the agent's autonomy, togglable via the Web UI or CLI:
*   **Plan Approval**: Review and approve the agent's proposed plan before execution begins.
*   **Step Approval**: Review each individual step (code/tool call) before it runs.
*   **Feedback Injection**: Provide corrections or guidance during the approval process to force replanning.

### 🔌 Model Context Protocol (MCP)
The system uses MCP to standardize tool usage. It supports multiple MCP servers configured via `config/mcp_server_config.yaml`.

### 🧪 Test Simulator
A built-in simulation framework to run batch tests, measure performance, and generate detailed HTML reports.

## 🚀 Setup & Installation

### Prerequisites
*   **Python 3.10+**
*   **uv** (Fast Python package installer)
*   **Git**

### Installation
1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd eag-v2-s10
    ```

2.  **Install dependencies using `uv`:**
    ```bash
    uv sync
    ```

3.  **Configure Environment:**
    Create a `.env` file in the root directory and add your API keys:
    ```env
    GEMINI_API_KEY=your_gemini_api_key_here
    ```

4.  **Configure MCP Servers:**
    Ensure `config/mcp_server_config.yaml` is set up with your desired MCP servers.

## 💻 Usage

### 1. Web Interface (Recommended)
The Web UI provides a ChatGPT-like experience with real-time updates, markdown rendering, and HITL controls.

**Start the Server:**
```bash
uv run uvicorn server:app --reload
```
*   Open your browser at: `http://127.0.0.1:8000`
*   Use the sidebar to toggle **Plan Approval** and **Step Approval**.

### 2. Command Line Interface (CLI)
For a lightweight, terminal-based experience.

**Start the CLI:**
```bash
uv run main.py
```

**CLI Commands:**
*   `/hitl on` / `/hitl off`: Toggle Plan Approval.
*   `/step on` / `/step off`: Toggle Step Approval.
*   `exit` / `quit`: Close the application.

## 📊 Running Tests (Simulator)

The project includes a comprehensive simulator to validate agent performance across various categories (Math, Memory, Web Search, RAG, Complex).

**Run All Tests:**
```bash
uv run simulator/run_tests.py
```

**Run Specific Range:**
```bash
uv run simulator/run_tests.py --start 1 --end 10
```

**View Reports:**
After the tests complete, open the generated HTML reports in your browser:
*   `simulator/report_details.html`: Detailed breakdown of every test case.
*   `simulator/report_stats.html`: High-level statistics and pass rates.

## 📂 Project Structure

```
eag-v2-s10/
├── agents/                 # Agent implementations (Decision, Executor, Perception, etc.)
├── config/                 # Configuration files (MCP servers, models)
├── mcp_servers/            # MCP server implementations and tools
├── memory/                 # Session memory storage (JSON)
├── memory_utils/           # Memory management logic (FAISS, initialization)
├── simulator/              # Test simulator, test cases, and report generators
├── static/                 # Frontend assets (HTML, JS, CSS)
├── utils/                  # Utility functions (retry logic, etc.)
├── agent_state.py          # Blackboard state definition
├── coordinator.py          # Main orchestration logic
├── main.py                 # CLI Entry point
├── server.py               # Web Server (FastAPI) Entry point
└── README.md               # Project documentation
```

## 🤝 Contributing
1.  Fork the repository.
2.  Create a feature branch.
3.  Commit your changes.
4.  Push to the branch.
5.  Open a Pull Request.
