import unittest
import os
import psycopg2
from dotenv import load_dotenv
import logging

# Import our modules
from instagram_pipeline.database.setup import create_database, create_tables
from instagram_pipeline.scraper.instagram_scraper import InstagramScraper
from instagram_pipeline.analysis.interest_analyzer import InterestAnalyzer


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("PipelineTest")

class TestInstagramPipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Set up test environment once before all tests"""
        load_dotenv()
        
        # Initialize database with test prefix
        os.environ['DB_NAME'] = 'instagram_test_db'
        create_database()
        create_tables()
        
        # Get database connection
        cls.db_conn = psycopg2.connect(
            host=os.getenv('DB_HOST'),
            port=os.getenv('DB_PORT'),
            dbname=os.getenv('DB_NAME'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD')
        )
        
        # Initialize components with test database
        cls.scraper = InstagramScraper(cls.db_conn)
        cls.analyzer = InterestAnalyzer()
        
        # Test username (use a public account for testing)
        cls.test_username = "instagram"
    
    @classmethod
    def tearDownClass(cls):
        """Clean up after all tests"""
        if cls.db_conn:
            cls.db_conn.close()
    
    def test_1_database_connection(self):
        """Test database connection"""
        cursor = self.db_conn.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        self.assertEqual(result[0], 1)
    
    def test_2_user_profile_scraping(self):
        """Test user profile scraping"""
        try:
            user_data = self.scraper.get_user_profile(self.test_username)
            self.assertIsNotNone(user_data)
            self.assertEqual(user_data["username"], self.test_username)
            
            # Verify data was stored in database
            cursor = self.db_conn.cursor()
            cursor.execute("SELECT username FROM users WHERE username = %s", (self.test_username,))
            result = cursor.fetchone()
            self.assertEqual(result[0], self.test_username)
            
        except Exception as e:
            self.fail(f"Profile scraping failed with error: {str(e)}")
    
    def test_3_follower_scraping(self):
        """Test follower scraping with a small limit"""
        try:
            # For testing, we'll limit the followers to just 5
            self.scraper.get_followers(self.test_username, max_count=5)
            
            # Verify followers were stored in database
            cursor = self.db_conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM followers f
                JOIN users u ON f.user_id = u.user_id
                WHERE u.username = %s
            """, (self.test_username,))
            count = cursor.fetchone()[0]
            
            self.assertGreater(count, 0)
            
        except Exception as e:
            self.fail(f"Follower scraping failed with error: {str(e)}")
    
    def test_4_following_scraping(self):
        """Test following scraping with a small limit"""
        try:
            # For testing, we'll limit the following to just 5
            self.scraper.get_following(self.test_username, max_count=5)
            
            # Verify following were stored in database
            cursor = self.db_conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM following f
                JOIN users u ON f.user_id = u.user_id
                WHERE u.username = %s
            """, (self.test_username,))
            count = cursor.fetchone()[0]
            
            self.assertGreater(count, 0)
            
        except Exception as e:
            self.fail(f"Following scraping failed with error: {str(e)}")
    
    def test_5_mutual_calculation(self):
        """Test mutual followers calculation"""
        try:
            self.scraper.calculate_mutual_followers(self.test_username)
            
            # Verify mutuals were calculated and stored
            cursor = self.db_conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM mutuals m
                JOIN users u ON m.user_id = u.user_id
                WHERE u.username = %s
            """, (self.test_username,))
            count = cursor.fetchone()[0]
            
            # We don't assert a specific count since it depends on the actual data
            logger.info(f"Found {count} mutual followers for {self.test_username}")
            
        except Exception as e:
            self.fail(f"Mutual calculation failed with error: {str(e)}")
    
    def test_6_interest_analysis(self):
        """Test interest analysis"""
        try:
            self.analyzer.analyze_user_interests(self.test_username)
            
            # Verify interests were stored in database
            cursor = self.db_conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM interests i
                JOIN users u ON i.user_id = u.user_id
                WHERE u.username = %s
            """, (self.test_username,))
            count = cursor.fetchone()[0]
            
            self.assertGreater(count, 0)
            
        except Exception as e:
            self.fail(f"Interest analysis failed with error: {str(e)}")

if __name__ == "__main__":
    unittest.main()