import pymupdf4llm
import re
import os

pdf_path = r"d:\Himanshu\EAG-V2\eag-v2-s10\mcp_servers\documents\DLF_13072023190044_BRSR.pdf"

if not os.path.exists(pdf_path):
    print(f"File not found: {pdf_path}")
    exit(1)

print(f"Extracting text from {pdf_path}...")
try:
    markdown = pymupdf4llm.to_markdown(pdf_path)
    
    if "Camellias" in markdown:
        print("✅ Found 'Camellias' in PDF!")
        # Print context
        matches = re.findall(r"(.{0,50}Camellias.{0,50})", markdown, re.IGNORECASE)
        for m in matches:
            print(f"Context: ...{m}...")
    else:
        print("❌ 'Camellias' NOT found in PDF.")
        
except Exception as e:
    print(f"Error extracting PDF: {e}")
