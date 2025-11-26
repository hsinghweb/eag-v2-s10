"""
Memory Validator - Validates cached memory entries before use
"""

from datetime import datetime, timezone
from typing import Dict, Any

# Freshness keywords that indicate user wants current information
FRESHNESS_KEYWORDS = ["current", "latest", "now", "today", "updated", "recent", "new"]

def get_age_hours(timestamp_str: str) -> float:
    """Calculate age of memory entry in hours"""
    try:
        timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        now = datetime.now(timezone.utc)
        age = (now - timestamp).total_seconds() / 3600
        return age
    except Exception:
        return float('inf')  # If can't parse, treat as very old

def is_memory_valid(memory_entry: dict, original_query: str = "") -> bool:
    """
    Validate if memory entry should be used based on:
    - Confidence score
    - Freshness (age vs TTL)
    - Source reliability
    - Query freshness keywords
    
    Args:
        memory_entry: Memory metadata dict with keys:
            - confidence: float
            - timestamp: ISO format string
            - ttl_hours: int
            - source: str
            - query: str (original query that generated this answer)
        original_query: Current user query (to detect freshness keywords)
    
    Returns:
        bool: True if memory should be used, False otherwise
    """
    
    # Check confidence threshold
    confidence = memory_entry.get("confidence", 0.0)
    if confidence < 0.9:
        print(f"[MEMORY_VALIDATOR] Rejected: Low confidence ({confidence})")
        return False
    
    # Check freshness
    timestamp = memory_entry.get("timestamp")
    if not timestamp:
        print(f"[MEMORY_VALIDATOR] Rejected: No timestamp")
        return False
    
    age_hours = get_age_hours(timestamp)
    ttl = memory_entry.get("ttl_hours", 168)  # Default 7 days
    
    if age_hours > ttl:
        print(f"[MEMORY_VALIDATOR] Rejected: Expired (age: {age_hours:.1f}h > TTL: {ttl}h)")
        return False
    
    # Check source-specific freshness
    source = memory_entry.get("source", "").lower()
    
    # Web search results expire faster
    if "web_search" in source and age_hours > 24:
        print(f"[MEMORY_VALIDATOR] Rejected: Web result too old ({age_hours:.1f}h)")
        return False
    
    # Detect freshness keywords in current query
    query_to_check = original_query.lower() if original_query else memory_entry.get("query", "").lower()
    
    if any(keyword in query_to_check for keyword in FRESHNESS_KEYWORDS):
        # User wants fresh data - memory must be very recent
        if age_hours > 1:
            print(f"[MEMORY_VALIDATOR] Rejected: Freshness keyword detected, data too old ({age_hours:.1f}h)")
            return False
    
    print(f"[MEMORY_VALIDATOR] Accepted: confidence={confidence}, age={age_hours:.1f}h, source={source}")
    return True


def should_index_to_memory(
    confidence: float,
    source: str,
    answer: str,
    goal_achieved: bool
) -> bool:
    """
    Decide if an answer should be indexed to memory FAISS.
    
    Args:
        confidence: Perception confidence score (0.0-1.0)
        source: Where the answer came from (e.g., "documents", "web_search")
        answer: The answer text
        goal_achieved: Whether the goal was achieved
    
    Returns:
        bool: True if should index, False otherwise
    """
    
    # Must be successful
    if not goal_achieved:
        print(f"[MEMORY_INDEXER] Skip: Goal not achieved")
        return False
    
    # Must have high confidence
    if confidence < 0.9:
        print(f"[MEMORY_INDEXER] Skip: Low confidence ({confidence})")
        return False
    
    # Must have substantial answer (not error message)
    if len(answer) < 20:
        print(f"[MEMORY_INDEXER] Skip: Answer too short ({len(answer)} chars)")
        return False
    
    # Check for error indicators
    error_indicators = ["error", "failed", "not found", "could not", "unable to"]
    if any(indicator in answer.lower() for indicator in error_indicators):
        print(f"[MEMORY_INDEXER] Skip: Answer contains error indicators")
        return False
    
    # Prefer document-sourced answers
    source_lower = source.lower()
    if "local documents" in source_lower or "rag" in source_lower or "documents" in source_lower:
        print(f"[MEMORY_INDEXER] Accept: Document-sourced answer (confidence={confidence})")
        return True
    
    # Web search results: only if very high confidence
    if "web_search" in source_lower or "web" in source_lower:
        if confidence >= 0.95:
            print(f"[MEMORY_INDEXER] Accept: High-confidence web result (confidence={confidence})")
            return True
        else:
            print(f"[MEMORY_INDEXER] Skip: Web result needs confidence >= 0.95 (got {confidence})")
            return False
    
    # Default: accept if high confidence
    print(f"[MEMORY_INDEXER] Accept: High confidence ({confidence}), source={source}")
    return True


def calculate_ttl_hours(source: str) -> int:
    """
    Calculate TTL (time-to-live) in hours based on source.
    
    Args:
        source: Source of the answer
    
    Returns:
        int: TTL in hours
    """
    source_lower = source.lower()
    
    if "web_search" in source_lower or "web" in source_lower:
        return 6  # Web results expire in 6 hours (reduced from 24h)
    elif "documents" in source_lower or "rag" in source_lower or "local" in source_lower:
        return 168  # Document-based: 7 days (reduced from 30 days)
    else:
        return 24  # Default: 1 day (reduced from 7 days)
