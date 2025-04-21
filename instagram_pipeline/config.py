import os
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_db_connection():
    """Get a connection to the PostgreSQL database"""
    return psycopg2.connect(
        host=os.getenv('DB_HOST'),
        port=os.getenv('DB_PORT'),
        dbname=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD')
    )

def get_instagram_credentials():
    """Get Instagram login credentials"""
    return {
        'username': os.getenv('INSTAGRAM_USERNAME'),
        'password': os.getenv('INSTAGRAM_PASSWORD')
    }

def get_openai_api_key():
    """Get OpenAI API key"""
    return os.getenv('OPENAI_API_KEY')

def get_proxy_api_key():
    """Get proxy service API key"""
    return os.getenv('PROXY_SERVICE_API')