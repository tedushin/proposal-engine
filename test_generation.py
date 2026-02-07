import google.generativeai as genai
import os
import argparse
import json

print("DEBUG: Starting generation test")

def test_genai(api_key):
    print("DEBUG: Configuring GenAI")
    genai.configure(api_key=api_key)
    print("DEBUG: Listing models")
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                print(f"Model: {m.name}")
    except Exception as e:
        print(f"ERROR: List models failed: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--api_key', required=True)
    args = parser.parse_args()
    test_genai(args.api_key)
