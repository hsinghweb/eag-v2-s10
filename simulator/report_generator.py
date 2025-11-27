import json
import os
from datetime import datetime

def generate_reports(history_file="simulator/test_history.json", output_dir="simulator"):
    """Generates HTML reports from the test history JSON."""
    
    if not os.path.exists(history_file):
        print(f"⚠️ History file not found: {history_file}")
        return

    with open(history_file, "r", encoding="utf-8") as f:
        history = json.load(f)

    # 1. Generate Detail Report (Query | Plan | Result)
    generate_detail_report(history, output_dir)

    # 2. Generate Stats Report (Tool Usage)
    generate_stats_report(history, output_dir)

def generate_detail_report(history, output_dir):
    html = """
    <html>
    <head>
        <title>Test Simulation Report - Details</title>
        <style>
            body { font-family: sans-serif; margin: 20px; }
            table { border-collapse: collapse; width: 100%; }
            th, td { border: 1px solid #ddd; padding: 8px; text-align: left; vertical-align: top; }
            th { background-color: #f2f2f2; }
            tr:nth-child(even) { background-color: #f9f9f9; }
            .plan { white-space: pre-wrap; font-family: monospace; font-size: 0.9em; }
            .result { white-space: pre-wrap; }
        </style>
    </head>
    <body>
        <h1>Test Simulation Report - Details</h1>
        <p>Generated: """ + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + """</p>
        <table>
            <tr>
                <th>ID</th>
                <th>Category</th>
                <th>Query</th>
                <th>Plan</th>
                <th>Result</th>
                <th>Status</th>
                <th>Time (s)</th>
            </tr>
    """

    for entry in history:
        plan_html = ""
        if "plan" in entry and entry["plan"]:
             for step in entry["plan"]:
                 plan_html += f"Step {step.get('step_index')}: {step.get('description')} [{step.get('status')}]<br>"

        html += f"""
            <tr>
                <td>{entry.get('id')}</td>
                <td>{entry.get('category')}</td>
                <td>{entry.get('query')}</td>
                <td class="plan">{plan_html}</td>
                <td class="result">{entry.get('result')}</td>
                <td>{entry.get('status')}</td>
                <td>{entry.get('duration', 0):.2f}</td>
            </tr>
        """

    html += """
        </table>
    </body>
    </html>
    """

    with open(os.path.join(output_dir, "report_details.html"), "w", encoding="utf-8") as f:
        f.write(html)
    print(f"✅ Generated: {os.path.join(output_dir, 'report_details.html')}")

def generate_stats_report(history, output_dir):
    # Calculate Stats
    tool_stats = {} # {tool_name: {success: 0, failure: 0}}
    
    for entry in history:
        if "tool_usage" in entry:
            for tool, result in entry["tool_usage"]:
                if tool not in tool_stats:
                    tool_stats[tool] = {"success": 0, "failure": 0}
                
                if result == "success":
                    tool_stats[tool]["success"] += 1
                else:
                    tool_stats[tool]["failure"] += 1

    html = """
    <html>
    <head>
        <title>Test Simulation Report - Tool Statistics</title>
        <style>
            body { font-family: sans-serif; margin: 20px; }
            table { border-collapse: collapse; width: 50%; }
            th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
            th { background-color: #f2f2f2; }
            tr:nth-child(even) { background-color: #f9f9f9; }
        </style>
    </head>
    <body>
        <h1>Test Simulation Report - Tool Statistics</h1>
        <p>Generated: """ + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + """</p>
        <table>
            <tr>
                <th>Tool Name</th>
                <th>Successes</th>
                <th>Failures</th>
                <th>Total Calls</th>
                <th>Success Rate</th>
            </tr>
    """

    for tool, stats in sorted(tool_stats.items()):
        total = stats["success"] + stats["failure"]
        rate = (stats["success"] / total * 100) if total > 0 else 0
        
        html += f"""
            <tr>
                <td>{tool}</td>
                <td>{stats['success']}</td>
                <td>{stats['failure']}</td>
                <td>{total}</td>
                <td>{rate:.1f}%</td>
            </tr>
        """

    html += """
        </table>
    </body>
    </html>
    """

    with open(os.path.join(output_dir, "report_stats.html"), "w", encoding="utf-8") as f:
        f.write(html)
    print(f"✅ Generated: {os.path.join(output_dir, 'report_stats.html')}")
