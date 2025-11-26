import asyncio
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

class IOHandler(ABC):
    """Abstract base class for Input/Output handling (CLI vs Web)"""
    
    @abstractmethod
    async def output(self, message_type: str, data: Any):
        """
        Send data to the interface.
        message_type: 'log', 'step', 'plan', 'answer', 'error', 'perception', 'retrieval'
        data: The content to display
        """
        pass

    @abstractmethod
    async def input(self, prompt: str, data: Any = None) -> str:
        """
        Request input from the user (HITL).
        prompt: The question to ask the user
        data: Optional context (e.g., the plan step being reviewed)
        Returns: User's response string
        """
        pass

class CLIIOHandler(IOHandler):
    """Implementation for Command Line Interface"""
    
    async def output(self, message_type: str, data: Any):
        if message_type == "log":
            print(data)
        elif message_type == "step":
            step = data
            print(f"\n--- ⚙️ Step {step['step_index']} Execution ---")
            print(f"Description: {step['description']}")
            if step.get('code'):
                print(f"Code:\n{step['code']}")
        elif message_type == "plan":
            step = data
            print(f"\n📋 Proposed Plan Step {step['step_index']}: {step['description']}")
            if step.get('code'):
                print(f"   Code:\n{step['code']}")
        elif message_type == "answer":
            print(f"\n🎉 Final Answer: {data['answer']}")
            print(f"📚 Source: {data['source']}")
        elif message_type == "error":
            print(f"\n❌ Error: {data}")
        elif message_type == "perception":
            print(f"\n--- 🧠 Perception ({data['type']}) ---")
            if data.get('goal'):
                print(f"Goal: {data['goal']}")
            if data.get('summary'):
                print(f"✅ Goal Achieved: {data['summary']}")
        elif message_type == "retrieval":
            print("\n--- 🔍 Retriever ---")
            # Retrieval details are usually logged, maybe just a header here
        elif message_type == "decision":
            print(f"\n--- 📝 Decision ({data['mode']}) ---")

    async def input(self, prompt: str, data: Any = None) -> str:
        print(f"\n🛑 HITL: {prompt}")
        if data:
            # For CLI, we might have already printed the plan, but let's be safe
            pass 
        return await asyncio.to_thread(input, "👉 Your input (Enter to approve, or type feedback): ")
