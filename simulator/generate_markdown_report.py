"""
Generate a Markdown report from test_history.json for GitHub viewing
Usage: uv run simulator/generate_markdown_report.py
"""

import json
import os
from datetime import datetime

def generate_markdown_report():
    # Read test history
    history_file = "simulator/test_history.json"
    output_file = "simulator/REPORT.md"
    
    with open(history_file, "r", encoding="utf-8") as f:
        history = json.load(f)
    
    # Sort by ID
    history = sorted(history, key=lambda x: x.get("id", 0))
    
    # Generate Markdown
    md = f"""# Test Simulation Report

**Generated:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}  
**Total Tests:** {len(history)}

---

## Summary Statistics

"""
    
    # Calculate statistics
    total_tests = len(history)
    successful_tests = sum(1 for t in history if t.get("status") == "success")
    failed_tests = sum(1 for t in history if t.get("status") == "error")
    total_duration = sum(t.get("duration", 0) for t in history)
    avg_duration = total_duration / total_tests if total_tests > 0 else 0
    
    md += f"""| Metric | Value |
|--------|-------|
| Total Tests | {total_tests} |
| Successful | {successful_tests} |
| Failed | {failed_tests} |
| Success Rate | {(successful_tests/total_tests*100):.1f}% |
| Total Duration | {total_duration:.2f}s |
| Average Duration | {avg_duration:.2f}s |

---

## Test Results

"""
    
    # Group by category
    categories = {}
    for test in history:
        cat = test.get("category", "Unknown")
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(test)
    
    # Generate test details by category
    for category, tests in sorted(categories.items()):
        md += f"\n### {category} ({len(tests)} tests)\n\n"
        
        for test in tests:
            test_id = test.get("id")
            query = test.get("query")
            result = test.get("result", "No result")
            status = test.get("status", "unknown")
            duration = test.get("duration", 0)
            
            # Status emoji
            status_emoji = "✅" if status == "success" else "❌"
            
            md += f"#### {status_emoji} Test {test_id}: {query}\n\n"
            md += f"**Status:** {status}  \n"
            md += f"**Duration:** {duration:.2f}s  \n"
            md += f"**Result:** {result}\n\n"
            
            # Plan summary
            plan = test.get("plan", [])
            if plan:
                md += f"**Plan Steps:** {len(plan)}\n\n"
                for i, step in enumerate(plan[:3], 1):  # Show first 3 steps
                    step_type = step.get("type", "UNKNOWN")
                    step_desc = step.get("description", "No description")
                    md += f"{i}. `{step_type}` - {step_desc}\n"
                
                if len(plan) > 3:
                    md += f"... and {len(plan) - 3} more steps\n"
                md += "\n"
            
            md += "---\n\n"
    
    # Tool usage statistics
    md += "\n## Tool Usage Statistics\n\n"
    
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
            md += f"| {tool} | {stats['success']} | {stats['failure']} | {total} | {rate:.1f}% |\n"
    else:
        md += "*No tool usage data available.*\n"
    
    # Write to file
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(md)
    
    print(f"✅ Markdown report generated: {output_file}")

if __name__ == "__main__":
    generate_markdown_report()
