from ddgs import DDGS
import time

print("DEBUG: Starting simple search test...")
try:
    with DDGS(timeout=10) as ddgs:
        print("DEBUG: DDGS initialized. Sending query...")
        results = [r for r in ddgs.text("test", max_results=1)]
        print(f"DEBUG: Search successful. Found {len(results)} results.")
        if results:
            print(f"DEBUG: Result 1: {results[0]['title']}")
except Exception as e:
    print(f"ERROR: Search failed with error: {e}")

print("DEBUG: Test finished.")
