# filename: list_openai_models.py
import os
from openai import OpenAI, APIError
from dotenv import load_dotenv

# Load environment variables (especially OPENAI_API_KEY)
load_dotenv()

# Configure the API key
api_key = os.getenv('OPENAI_API_KEY')
if not api_key:
    print("Error: OPENAI_API_KEY not found in environment variables.")
    print("Please ensure you have a .env file with OPENAI_API_KEY=your_key or set the environment variable.")
    exit(1)

print("Initializing OpenAI client...")
try:
    # Initialize the OpenAI client
    # The client automatically uses the OPENAI_API_KEY environment variable if not passed explicitly
    client = OpenAI()
    print("OpenAI client initialized successfully.")
except Exception as e:
    print(f"Error initializing OpenAI client: {e}")
    exit(1)

print("\nFetching available OpenAI models...")

try:
    models_found = False
    # Iterate through available models using the client
    for model in client.models.list():
        # You might want to filter or just list all models by their ID
        print(f"- Model ID: {model.id}")
        # You could add more details if needed, e.g., model.owned_by
        # print(f"  Owned by: {model.owned_by}")
        # print("-" * 20)
        models_found = True

    if not models_found:
        print("No models found for your API key.")
    else:
        print("\nListing complete.")

except APIError as e:
    print(f"\nAn OpenAI API error occurred: {e}")
except Exception as e:
    print(f"\nAn unexpected error occurred while listing models: {e}")
