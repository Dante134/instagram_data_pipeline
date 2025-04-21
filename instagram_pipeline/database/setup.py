import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import os
from dotenv import load_dotenv

load_dotenv()

def create_database():
    # Connect to PostgreSQL
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST'),
        port=os.getenv('DB_PORT'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD')
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()
    
    # Create database if it doesn't exist
    cursor.execute("SELECT 1 FROM pg_catalog.pg_database WHERE datname = %s", (os.getenv('DB_NAME'),))
    if not cursor.fetchone():
        cursor.execute(f"CREATE DATABASE {os.getenv('DB_NAME')}")
    
    cursor.close()
    conn.close()

def create_tables():
    # Connect to our database
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST'),
        port=os.getenv('DB_PORT'),
        dbname=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD')
    )
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id VARCHAR(255) PRIMARY KEY,
        username VARCHAR(255) NOT NULL,
        full_name VARCHAR(255),
        bio TEXT,
        profile_pic_url TEXT,
        follower_count INT,
        following_count INT,
        is_private BOOLEAN,
        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    
    # Create followers table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS followers (
        id SERIAL PRIMARY KEY,
        user_id VARCHAR(255) REFERENCES users(user_id),
        follower_id VARCHAR(255) REFERENCES users(user_id),
        follow_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, follower_id)
    );
    """)
    
    # Create following table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS following (
        id SERIAL PRIMARY KEY,
        user_id VARCHAR(255) REFERENCES users(user_id),
        following_id VARCHAR(255) REFERENCES users(user_id),
        follow_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, following_id)
    );
    """)
    
    # Create mutuals table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS mutuals (
        id SERIAL PRIMARY KEY,
        user_id VARCHAR(255) REFERENCES users(user_id),
        mutual_id VARCHAR(255) REFERENCES users(user_id),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, mutual_id)
    );
    """)
    
    # Create interest categories table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS interest_categories (
        category_id SERIAL PRIMARY KEY,
        category_name VARCHAR(255) NOT NULL,
        parent_category_id INT REFERENCES interest_categories(category_id) NULL,
        description TEXT,
        UNIQUE(category_name)
    );
    """)
    
    # Create interests table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS interests (
        id SERIAL PRIMARY KEY,
        user_id VARCHAR(255) REFERENCES users(user_id),
        category_id INT REFERENCES interest_categories(category_id),
        confidence_score FLOAT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, category_id)
    );
    """)
    
    # Create scrape_jobs table for tracking scraping progress
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS scrape_jobs (
        job_id SERIAL PRIMARY KEY,
        target_username VARCHAR(255) NOT NULL,
        job_type VARCHAR(50) NOT NULL,
        status VARCHAR(50) DEFAULT 'pending',
        started_at TIMESTAMP,
        completed_at TIMESTAMP,
        last_cursor VARCHAR(255),
        total_items INT,
        processed_items INT DEFAULT 0,
        error_message TEXT
    );
    """)
    
    conn.commit()
    cursor.close()
    conn.close()

if __name__ == "__main__":
    create_database()
    create_tables()
    print("Database and tables created successfully!")