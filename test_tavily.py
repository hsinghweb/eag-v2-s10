import os
from dotenv import load_dotenv
from tavily import TavilyClient

# Load environment variables
load_dotenv()

# Get API key
api_key = os.getenv("TAVILY_API_KEY")

if not api_key:
    print("❌ ERROR: TAVILY_API_KEY not found in .env file")
    print("Please add: TAVILY_API_KEY=tvly-your-key-here")
    exit(1)

print(f"✅ API Key found: {api_key[:10]}...")

# Test Tavily search
try:
    print("\n🔍 Testing Tavily search...")
    client = TavilyClient(api_key=api_key)
    
    response = client.search(
        query="Who is the current Prime Minister of India?",
        max_results=3,
        include_answer=False,
        include_raw_content=False
    )
    
    results = response.get('results', [])
    
    if results:
        print(f"\n✅ SUCCESS! Found {len(results)} results:\n")
        for i, result in enumerate(results, 1):
            print(f"{i}. {result.get('title', 'No Title')}")
            print(f"   URL: {result.get('url', 'No URL')}")
            print(f"   Summary: {result.get('content', 'No Summary')[:150]}...")
            print()
    else:
        print("⚠️ No results returned")
        
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    print(f"Error type: {type(e).__name__}")
