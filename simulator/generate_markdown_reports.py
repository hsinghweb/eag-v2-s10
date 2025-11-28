"""
Generate two separate Markdown reports from test_history.json
- REPORT_DETAILS.md: Query | Plan | Result table
- REPORT_STATS.md: Tool usage statistics

Usage: uv run simulator/generate_markdown_reports.py
"""

import json
from datetime import datetime

def generate_details_report():
    """Generate detailed test results report"""
    history_file = "simulator/test_history.json"
    output_file = "simulator/REPORT_DETAILS.md"
    
    with open(history_file, "r", encoding="utf-8") as f:
        history = json.load(f)
    
    # Sort by ID
    history = sorted(history, key=lambda x: x.get("id", 0))
    
    md = f"""# Test Simulation Report - Details

**Generated:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}  
**Total Tests:** {len(history)}

---

## Test Results

| ID | Category | Query | Plan | Result | Status | Time (s) |
|----|----------|-------|------|--------|--------|----------|
"""
    
    for test in history:
        test_id = test.get("id")
        category = test.get("category", "Unknown")
        query = test.get("query", "")
        result = test.get("result", "No result")
        status = test.get("status", "unknown")
        duration = test.get("duration", 0)
        
        # Status emoji
        status_emoji = "✅" if status == "success" else "❌"
        
        # Plan summary
        plan = test.get("plan", [])
        plan_summary = ""
        if plan:
            for i, step in enumerate(plan[:2], 1):  # Show first 2 steps
                step_type = step.get("type", "?")
                step_desc = step.get("description", "")[:50]  # Truncate
                plan_summary += f"{i}. `{step_type}`: {step_desc}...<br>"
            
            if len(plan) > 2:
                plan_summary += f"*+{len(plan) - 2} more*"
        else:
            plan_summary = "*No plan*"
        
        # Escape pipe characters in text
        query = query.replace("|", "\\|")
        result = result.replace("|", "\\|")[:100]  # Truncate result
        
        md += f"| {test_id} | {category} | {query} | {plan_summary} | {result} | {status_emoji} {status} | {duration:.2f} |\n"
    
    md += "\n---\n\n*Note: Plan and Result columns are truncated for readability. See full details in test_history.json*\n"
    
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(md)
    
    print(f"✅ Details report generated: {output_file}")

def generate_stats_report():
    """Generate tool usage statistics report"""
    history_file = "simulator/test_history.json"
    output_file = "simulator/REPORT_STATS.md"
    
    with open(history_file, "r", encoding="utf-8") as f:
        history = json.load(f)
    
    # Calculate statistics
    total_tests = len(history)
    successful_tests = sum(1 for t in history if t.get("status") == "success")
    failed_tests = sum(1 for t in history if t.get("status") == "error")
    total_duration = sum(t.get("duration", 0) for t in history)
    avg_duration = total_duration / total_tests if total_tests > 0 else 0
    
    md = f"""# Test Simulation Report - Statistics

**Generated:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

---

## Overall Statistics

| Metric | Value |
|--------|-------|
| Total Tests | {total_tests} |
| Successful | {successful_tests} |
| Failed | {failed_tests} |
| Success Rate | {(successful_tests/total_tests*100):.1f}% |
| Total Duration | {total_duration:.2f}s |
| Average Duration | {avg_duration:.2f}s |

---

## Tool Usage Statistics

"""
    
    # Calculate tool stats
    tool_stats = {}
    for test in history:
        for tool, result in test.get("tool_usage", []):
            if tool not in tool_stats:
                tool_stats[tool] = {"success": 0, "failure": 0}
            
            if result == "success":
                tool_stats[tool]["success"] += 1
            else:
                tool_stats[tool]["failure"] += 1
    
    if tool_stats:
        md += "| Tool Name | Successes | Failures | Total Calls | Success Rate |\n"
        md += "|-----------|-----------|----------|-------------|-------------|\n"
        
        for tool, stats in sorted(tool_stats.items()):
            total = stats["success"] + stats["failure"]
            rate = (stats["success"] / total * 100) if total > 0 else 0
            md += f"| `{tool}` | {stats['success']} | {stats['failure']} | {total} | {rate:.1f}% |\n"
    else:
        md += "*No tool usage data available.*\n"
    
    # Category breakdown
    md += "\n---\n\n## Category Breakdown\n\n"
    
    categories = {}
    for test in history:
        cat = test.get("category", "Unknown")
        status = test.get("status", "unknown")
        if cat not in categories:
            categories[cat] = {"success": 0, "error": 0}
        
        if status == "success":
            categories[cat]["success"] += 1
        else:
            categories[cat]["error"] += 1
    
    md += "| Category | Successful | Failed | Total | Success Rate |\n"
    md += "|----------|------------|--------|-------|-------------|\n"
    
    for cat, stats in sorted(categories.items()):
        total = stats["success"] + stats["error"]
        rate = (stats["success"] / total * 100) if total > 0 else 0
        md += f"| {cat} | {stats['success']} | {stats['error']} | {total} | {rate:.1f}% |\n"
    
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(md)
    
    print(f"✅ Statistics report generated: {output_file}")

if __name__ == "__main__":
    generate_details_report()
    generate_stats_report()
    print("\n🎉 Both Markdown reports generated successfully!")
