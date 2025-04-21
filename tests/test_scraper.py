import unittest
import os
import json
import psycopg2
import logging
from unittest.mock import patch, MagicMock
from dotenv import load_dotenv

# Import modules from the pipeline
from interest_analyzer import InterestAnalyzer
from database_setup import create_database, create_tables

class TestInterestAnalyzer(unittest.TestCase):
    """Test cases for the Interest Analyzer component"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment once before all tests"""
        # Configure logging
        logging.basicConfig(level=logging.INFO)
        cls.logger = logging.getLogger("AnalyzerTest")
        
        # Load environment variables
        load_dotenv()
        
        # Use test database
        os.environ['DB_NAME'] = 'instagram_test_db'
        
        # Initialize database with test prefix
        cls.logger.info("Setting up test database...")
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
        
        # Sample following data (used for mocking)
        cls.sample_following_data = [
            {
                "username": "fashionaccount",
                "full_name": "Fashion Blogger",
                "bio": "Fashion enthusiast. Sharing daily fashion tips and trends."
            },
            {
                "username": "techguru",
                "full_name": "Tech Expert",
                "bio": "Software engineer. AI enthusiast. Sharing tech news and tutorials."
            },
            {
                "username": "foodlover",
                "full_name": "Chef Michael",
                "bio": "Professional chef. Sharing recipes and food photography."
            }
        ]
        
        # Sample GPT-4 response
        cls.sample_gpt_response = {
            "results": [
                {
                    "username": "fashionaccount",
                    "category": "Fashion",
                    "confidence": 0.95
                },
                {
                    "username": "techguru",
                    "category": "Technology",
                    "confidence": 0.92
                },
                {
                    "username": "foodlover",
                    "category": "Food",
                    "confidence": 0.9
                }
            ]
        }
        
        # Test username (should exist in the test database)
        cls.test_username = "instagram"
        
        # Set up test user and mock relationships
        cursor = cls.db_conn.cursor()
        
        # Create test user if doesn't exist
        cursor.execute("""
            INSERT INTO users (user_id, username, full_name, bio)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (user_id) DO NOTHING
        """, ("12345", cls.test_username, "Test User", "This is a test user"))
        
        # Create sample following accounts
        for i, account in enumerate(cls.sample_following_data):
            cursor.execute("""
                INSERT INTO users (user_id, username, full_name, bio)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (user_id) DO NOTHING
            """, (
                f"following_{i}", 
                account["username"], 
                account["full_name"],
                account["bio"]
            ))
            
            # Add following relationship
            cursor.execute("""
                INSERT INTO following (user_id, following_id)
                VALUES (%s, %s)
                ON CONFLICT (user_id, following_id) DO NOTHING
            """, ("12345", f"following_{i}"))
        
        cls.db_conn.commit()
        cursor.close()
        
        # Initialize analyzer
        cls.analyzer = InterestAnalyzer()
    
    @classmethod
    def tearDownClass(cls):
        """Clean up after all tests"""
        cls.logger.info("Cleaning up test resources...")
        cls.analyzer.cleanup()
        if cls.db_conn:
            cls.db_conn.close()
    
    def setUp(self):
        """Setup before each test"""
        self.cursor = self.db_conn.cursor()
    
    def tearDown(self):
        """Cleanup after each test"""
        if self.cursor:
            self.cursor.close()
    
    def test_01_interest_categories_setup(self):
        """Test that interest categories are set up correctly"""
        self.logger.info("Testing interest categories setup")
        
        # Check main categories exist
        self.cursor.execute("""
            SELECT COUNT(*) FROM interest_categories
            WHERE parent_category_id IS NULL
        """)
        main_category_count = self.cursor.fetchone()[0]
        self.assertGreater(main_category_count, 5, "Not enough main categories found")
        
        # Check subcategories exist
        self.cursor.execute("""
            SELECT COUNT(*) FROM interest_categories
            WHERE parent_category_id IS NOT NULL
        """)
        sub_category_count = self.cursor.fetchone()[0]
        self.assertGreater(sub_category_count, 3, "Not enough subcategories found")
        
        self.logger.info(f"Found {main_category_count} main categories and {sub_category_count} subcategories")
    
    def test_02_get_category_mapping(self):
        """Test category mapping retrieval"""
        self.logger.info("Testing category mapping")
        
        category_mapping = self.analyzer.get_category_mapping()
        
        # Verify mapping has content
        self.assertIsNotNone(category_mapping, "Category mapping is None")
        self.assertGreater(len(category_mapping), 5, "Category mapping has too few entries")
        
        # Check specific categories exist
        expected_categories = ["Fashion", "Technology", "Sports", "Music"]
        for category in expected_categories:
            self.assertIn(category, category_mapping, f"Category '{category}' not found in mapping")
        
        self.logger.info(f"Category mapping has {len(category_mapping)} entries")
    
    def test_03_get_following_data(self):
        """Test retrieval of following data"""
        self.logger.info(f"Testing following data retrieval for {self.test_username}")
        
        # Get user ID for test username
        self.cursor.execute("SELECT user_id FROM users WHERE username = %s", (self.test_username,))
        user_id = self.cursor.fetchone()[0]
        
        # Get following data
        following_data = self.analyzer.get_following_data_for_user(user_id)
        
        # Verify data structure
        self.assertIsNotNone(following_data, "Following data is None")
        self.assertGreater(len(following_data), 0, "No following data returned")
        
        # Check data structure
        for account in following_data:
            self.assertIn("username", account, "Username missing in following data")
            self.assertIn("full_name", account, "Full name missing in following data")
        
        self.logger.info(f"Found {len(following_data)} following accounts")
    
    @patch('openai.OpenAI')
    def test_04_analyze_user_interests(self, mock_openai):
        """Test interest analysis with mock GPT response"""
        self.logger.info(f"Testing interest analysis for {self.test_username}")
        
        # Configure mock
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_message = MagicMock()
        mock_message.content = json.dumps(self.sample_gpt_response)
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        
        mock_client.chat.completions.create.return_value = mock_response
        
        # Override the analyzer's OpenAI client with our mock
        self.analyzer.client = mock_client
        
        # Run interest analysis
        self.analyzer.analyze_user_interests(self.test_username)
        
        # Verify GPT-4 was called
        mock_client.chat.completions.create.assert_called()
        
        # Verify interests were stored in database
        self.cursor.execute("""
            SELECT COUNT(*) FROM interests i
            JOIN users u ON i.user_id = u.user_id
            WHERE u.username = %s
        """, (self.test_username,))
        interest_count = self.cursor.fetchone()[0]
        
        self.assertGreater(interest_count, 0, "No interests were stored in database")
        self.logger.info(f"Found {interest_count} interests in database")
        
        # Check specific interests
        self.cursor.execute("""
            SELECT ic.category_name, i.confidence_score
            FROM interests i
            JOIN users u ON i.user_id = u.user_id
            JOIN interest_categories ic ON i.category_id = ic.category_id
            WHERE u.username = %s
        """, (self.test_username,))
        
        interests = self.cursor.fetchall()
        interest_dict = {row[0]: row[1] for row in interests}
        
        for result in self.sample_gpt_response["results"]:
            category = result["category"]
            if category in interest_dict:
                self.assertAlmostEqual(
                    interest_dict[category], 
                    result["confidence"],
                    places=1,
                    msg=f"Confidence score mismatch for {category}"
                )
    
    def test_05_batch_prompt_creation(self):
        """Test the creation of batch prompts for GPT-4"""
        self.logger.info("Testing batch prompt creation")
        
        # Get available categories
        categories = list(self.analyzer.get_category_mapping().keys())
        
        # Create a batch prompt
        prompt = self.analyzer._create_batch_prompt(self.sample_following_data, categories)
        
        # Verify prompt structure
        self.assertIn("available categories", prompt.lower(), "Categories not included in prompt")
        
        for account in self.sample_following_data:
            self.assertIn(account["username"], prompt, f"Username {account['username']} not in prompt")
            self.assertIn(account["bio"], prompt, f"Bio for {account['username']} not in prompt")
        
        self.assertIn("JSON", prompt, "JSON format instructions not in prompt")
        self.logger.info("Batch prompt creation verified")
    
    def test_06_process_pending_users(self):
        """Test processing of pending users for interest analysis"""
        self.logger.info("Testing pending users processing")
        
        # Create a completed scrape job for our test user
        self.cursor.execute("""
            INSERT INTO scrape_jobs (target_username, job_type, status, started_at, completed_at)
            VALUES (%s, %s, %s, NOW(), NOW())
            ON CONFLICT DO NOTHING
        """, (self.test_username, 'following', 'completed'))
        self.db_conn.commit()
        
        # Clear existing interests to ensure our user needs analysis
        self.cursor.execute("""
            DELETE FROM interests i
            USING users u
            WHERE i.user_id = u.user_id AND u.username = %s
        """, (self.test_username,))
        self.db_conn.commit()
        
        # Mock the analyze_user_interests method
        with patch.object(self.analyzer, 'analyze_user_interests') as mock_analyze:
            # Run the process
            self.analyzer.process_pending_users()
            
            # Check if our user was processed
            mock_analyze.assert_called()
            
            # Check if our test username was processed
            processed = False
            for call in mock_analyze.call_args_list:
                args, _ = call
                if args and args[0] == self.test_username:
                    processed = True
                    break
            
            self.assertTrue(processed, f"Test user {self.test_username} was not processed")
        
        self.logger.info("Pending users processing verified")

if __name__ == "__main__":
    unittest.main()