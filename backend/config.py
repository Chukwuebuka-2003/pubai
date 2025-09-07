import os
from dotenv import load_dotenv

load_dotenv()

# NCBI API details
BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
EMAIL = os.getenv("GMAIL_ADDRESS") # Default for testing, use .env
TOOL = "PubMedSearchApp"
NCBI_API_KEY = os.getenv("NCBI_API_KEY")

# JWT configuration
JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGORITHM = "HS256"

# Database configuration
# Use DATABASE_URL for PostgreSQL connection string from environment variable
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test.db") # Default to SQLite for local development if PG not configured
