# filename: list_google_models.py
import google.generativeai as genai
import os
from dotenv import load_dotenv

# Load environment variables (especially GEMINI_API_KEY)
load_dotenv()

# Configure the API key
api_key = os.getenv('GEMINI_API_KEY')
if not api_key:
    print("Error: GEMINI_API_KEY not found in environment variables.")
    print("Please ensure you have a .env file with GEMINI_API_KEY=your_key or set the environment variable.")
    exit(1)

try:
    genai.configure(api_key=api_key)
    print("Successfully configured Gemini API key.")
except Exception as e:
    print(f"Error configuring Gemini API: {e}")
    exit(1)

print("\nFetching available Google Generative AI models...")

try:
    models_found = False
    # Iterate through available models
    for m in genai.list_models():
        # Check if the model supports the 'generateContent' method (most common use case)
        if 'generateContent' in m.supported_generation_methods:
            models_found = True
            print(f"- Model Name: {m.name}")
            # print(f"  Description: {m.description}") # Uncomment for more detail
            # print(f"  Supported Methods: {m.supported_generation_methods}") # Uncomment for more detail
            # print("-" * 20) # Uncomment for separator

    if not models_found:
        print("No models supporting 'generateContent' found for your API key.")
    else:
        print("\nListing complete.")

except Exception as e:
    print(f"\nAn error occurred while listing models: {e}")
