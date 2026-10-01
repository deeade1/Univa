# Create: apps/backend/debug_simple.py
import os
import sys

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables manually
from dotenv import load_dotenv

# Load environment variables from .env.prod
env_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env.prod')
load_dotenv(env_path)

print("Environment variables:")
print(f"POSTGRES_USER: {os.getenv('POSTGRES_USER')}")
print(f"POSTGRES_PASSWORD: {os.getenv('POSTGRES_PASSWORD')}")
print(f"POSTGRES_DB: {os.getenv('POSTGRES_DB')}")
print(f"PGHOST: {os.getenv('PGHOST')}")
print(f"PGPORT: {os.getenv('PGPORT')}")

# Check if there are any other env files that might override
backend_env = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(backend_env):
    print(f"\nWARNING: Found backend/.env file that might override settings:")
    with open(backend_env, 'r') as f:
        print(f.read())