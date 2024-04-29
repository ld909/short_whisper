import os

api_key = os.environ.get("ANTHROPIC_API_KEY")

if api_key:
    print("ANTHROPIC_API_KEY is set to:", api_key)
else:
    print("ANTHROPIC_API_KEY is not set or empty.")
