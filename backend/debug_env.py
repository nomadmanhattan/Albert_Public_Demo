from dotenv import load_dotenv
import os

load_dotenv()
key = os.getenv("GOOGLE_API_KEY")
if key:
    print(f"Key loaded: {key[:4]}... (Length: {len(key)})")
    # Check for common issues
    if key.startswith('"') or key.startswith("'"):
        print("WARNING: Key starts with a quote character!")
    if " " in key:
        print("WARNING: Key contains spaces!")
else:
    print("Key NOT loaded")
