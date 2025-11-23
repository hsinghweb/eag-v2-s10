import os
import json
import sys
from pathlib import Path

# Ensure OpenAI package is installed
try:
    import openai
except ImportError:
    print("OpenAI package not installed. Please install it with 'pip install openai'.", file=sys.stderr)
    sys.exit(1)

# Retrieve API key from environment (expects OPENAI_API_KEY)
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("OPENAI_API_KEY not set in environment.", file=sys.stderr)
    sys.exit(1)
openai.api_key = api_key

# Question and context (hard‑coded for this demonstration)
question = "Who is the current Prime Minister of India?"
context = """{\n    'results': [\n        {\n            'url': 'https://ca.finance.yahoo.com/news/media-advisory-sunday-november-23-2025-news.html',\n            'title': 'Media Advisory - Sunday, November 23, 2025 - Yahoo Finance',\n            'content': 'The Prime Minister will meet with the Prime Minister of India, Narendra Modi. Note for media: Official photographers only.',\n            'score': 0.935964,\n            'raw_content': None\n        },\n        {\n            'url': 'https://www.mea.gov.in/press-releases.htm?dtl/40313/Visit_of_Prime_Minister_to_Johannesburg_South_Africa_for_the_G20_Leaders_Summit_November_21__23_2025',\n            'title': 'Visit of Prime Minister to Johannesburg, South Africa for the G20 ...',\n            'content': "Prime Minister Shri Narendra Modi will be visiting Johannesburg, South Africa on 21-23 November, 2025 to attend the 20th G20 Leaders' Summit",\n            'score': 0.8690161,\n            'raw_content': None\n        }\n    ],\n    'formatted': "Found 2 search results..."\n}"""

prompt = f"You are a helpful assistant. Use the following web search results as context to answer the question.\n\nContext:\n{context}\n\nQuestion: {question}\n\nAnswer:" 

response = openai.ChatCompletion.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": prompt}],
    temperature=0.0,
    max_tokens=200,
)

answer = response.choices[0].message.content.strip()
print(answer)
