"""
Standalone script to generate HTML reports from test_history.json
Usage: uv run simulator/generate_reports_only.py
"""

from report_generator import generate_reports

if __name__ == "__main__":
    print("📊 Generating HTML Reports from test_history.json...")
    generate_reports("test_history.json", ".")
    print("✅ Reports generated successfully!")
    print("   - report_details.html")
    print("   - report_stats.html")
