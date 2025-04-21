import os
import json
import time
import psycopg2
from dotenv import load_dotenv
import logging
from openai import OpenAI
import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("interest_analyzer.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("InterestAnalyzer")

class InterestAnalyzer:
    def __init__(self):
        load_dotenv()
        self.db_conn = self._get_db_connection()
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.setup_interest_categories()
        self.batch_size = 20  # Process 20 accounts at a time for efficiency
    
    def _get_db_connection(self):
        return psycopg2.connect(
            host=os.getenv('DB_HOST'),
            port=os.getenv('DB_PORT'),
            dbname=os.getenv('DB_NAME'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD')
        )
    
    def setup_interest_categories(self):
        """Set up predefined interest categories in the database"""
        categories = [
            # Main categories
            ("Fashion", None, "Clothing, style, and fashion trends"),
            ("Technology", None, "Technology products, software, and digital innovation"),
            ("Sports", None, "Athletic activities, teams, and sporting events"),
            ("Fitness", None, "Exercise, workouts, and physical health"),
            ("Food", None, "Cooking, recipes, restaurants, and culinary content"),
            ("Travel", None, "Destinations, trips, and travel experiences"),
            ("Art", None, "Visual arts, painting, sculpture, and artistic content"),
            ("Music", None, "Musicians, bands, concerts, and music content"),
            ("Photography", None, "Photos, cameras, and photography techniques"),
            ("Beauty", None, "Makeup, skincare, and beauty products"),
            ("Gaming", None, "Video games, gaming culture, and esports"),
            ("Business", None, "Entrepreneurship, finance, and professional content"),
            ("Entertainment", None, "Movies, TV shows, and celebrity content"),
            ("Education", None, "Learning, teaching, and educational resources"),
            ("Science", None, "Scientific discoveries, research, and concepts"),
            ("Politics", None, "Political figures, events, and discussions"),
            ("Lifestyle", None, "Home, family, personal development, and daily life"),
            ("Humor", None, "Comedy, memes, and funny content"),
            
            # Subcategories will be added with parent_id references
        ]
        
        cursor = self.db_conn.cursor()
        
        # Insert main categories first
        for category_name, parent_id, description in categories:
            cursor.execute("""
                INSERT INTO interest_categories (category_name, parent_category_id, description)
                VALUES (%s, %s, %s)
                ON CONFLICT (category_name) DO UPDATE 
                SET description = EXCLUDED.description
                RETURNING category_id
            """, (category_name, parent_id, description))
            
        self.db_conn.commit()
        
        # Now add subcategories (in a real implementation, we'd add many more)
        subcategories = [
            # Fashion subcategories
            ("Streetwear", "Fashion", "Urban and casual fashion styles"),
            ("Luxury Fashion", "Fashion", "High-end designer clothing and accessories"),
            ("Sustainable Fashion", "Fashion", "Eco-friendly and ethical fashion"),
            
            # Technology subcategories
            ("Mobile Tech", "Technology", "Smartphones, tablets, and mobile accessories"),
            ("AI & Machine Learning", "Technology", "Artificial intelligence and machine learning"),
            ("Programming", "Technology", "Software development and coding"),
            
            # Sports subcategories
            ("Football", "Sports", "Soccer/football teams and events"),
            ("Basketball", "Sports", "Basketball teams and events"),
            ("Formula 1", "Sports", "Formula 1 racing"),
            
            # Add more subcategories for other main categories
        ]
        
        # Insert subcategories with parent references
        for sub_name, parent_name, sub_description in subcategories:
            # Get parent category ID
            cursor.execute("SELECT category_id FROM interest_categories WHERE category_name = %s", (parent_name,))
            parent_id = cursor.fetchone()[0]
            
            cursor.execute("""
                INSERT INTO interest_categories (category_name, parent_category_id, description)
                VALUES (%s, %s, %s)
                ON CONFLICT (category_name) DO UPDATE 
                SET description = EXCLUDED.description
                RETURNING category_id
            """, (sub_name, parent_id, sub_description))
        
        self.db_conn.commit()
        logger.info("Interest categories setup completed")
    
    def get_category_mapping(self):
        """Get a mapping of category names to IDs"""
        cursor = self.db_conn.cursor()
        cursor.execute("SELECT category_id, category_name FROM interest_categories")
        return {row[1]: row[0] for row in cursor.fetchall()}
    
    def get_following_data_for_user(self, user_id):
        """Get following data for a user to analyze interests"""
        cursor = self.db_conn.cursor()
        cursor.execute("""
            SELECT u.username, u.full_name, u.bio
            FROM following f
            JOIN users u ON f.following_id = u.user_id
            WHERE f.user_id = %s
        """, (user_id,))
        
        following_data = []
        for row in cursor.fetchall():
            following_data.append({
                "username": row[0],
                "full_name": row[1],
                "bio": row[2] if row[2] else ""
            })
        
        return following_data
    
    def analyze_user_interests(self, username):
        """Analyze a user's interests based on their following list"""
        try:
            # Get user ID
            cursor = self.db_conn.cursor()
            cursor.execute("SELECT user_id FROM users WHERE username = %s", (username,))
            result = cursor.fetchone()
            if not result:
                logger.error(f"User {username} not found in database")
                return
            
            user_id = result[0]
            
            # Get following data
            following_data = self.get_following_data_for_user(user_id)
            
            if not following_data:
                logger.warning(f"No following data found for user {username}")
                return
            
            # Get all category names
            category_mapping = self.get_category_mapping()
            categories_list = list(category_mapping.keys())
            
            # Process following data in batches for efficiency
            total_processed = 0
            batch_results = []
            
            # Create batches of following data
            batches = [following_data[i:i + self.batch_size] for i in range(0, len(following_data), self.batch_size)]
            
            for batch_idx, batch in enumerate(batches):
                logger.info(f"Processing batch {batch_idx+1}/{len(batches)} for user {username}")
                
                # Create a prompt for GPT-4
                prompt = self._create_batch_prompt(batch, categories_list)
                
                # Send to GPT-4 and process response
                try:
                    response = self.client.chat.completions.create(
                        model="gpt-4",
                        messages=[
                            {"role": "system", "content": "You are an expert at analyzing Instagram accounts to determine interest categories. You must categorize accounts into the provided categories based on username, name, and bio text. Return results as a valid JSON array."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.2,
                        max_tokens=2000,
                        response_format={"type": "json_object"}
                    )
                    
                    # Extract and parse the result
                    result_json = json.loads(response.choices[0].message.content)
                    
                    if "results" in result_json:
                        batch_results.extend(result_json["results"])
                        total_processed += len(batch)
                        logger.info(f"Successfully processed {len(batch)} accounts for user {username}")
                    else:
                        logger.error(f"Invalid response format from GPT-4 for batch {batch_idx+1}")
                    
                    # Avoid rate limits
                    time.sleep(1)
                    
                except Exception as e:
                    logger.error(f"Error processing batch {batch_idx+1} with GPT-4: {str(e)}")
            
            # Process and store the interest analysis results
            if batch_results:
                self._store_interest_results(user_id, batch_results, category_mapping)
                logger.info(f"Successfully analyzed and stored interests for user {username}")
            else:
                logger.warning(f"No interest results generated for user {username}")
            
        except Exception as e:
            logger.error(f"Error analyzing interests for user {username}: {str(e)}")
    
    def _create_batch_prompt(self, batch, categories_list):
        """Create a prompt for processing a batch of following accounts"""
        categories_str = ", ".join(categories_list)
        
        prompt = f"""
        I need you to analyze the following Instagram accounts and determine which interest categories they fall into.
        
        The available categories are: {categories_str}
        
        For each account, return:
        1. The account username
        2. The most likely interest category (must be one from the list provided)
        3. A confidence score (0.0-1.0) of how confident you are in this categorization
        
        Here are the accounts to analyze:
        """
        
        for account in batch:
            prompt += f"\n---\nUsername: {account['username']}\n"
            prompt += f"Name: {account['full_name']}\n"
            prompt += f"Bio: {account['bio']}\n"
        
        prompt += """
        Return your analysis in a valid JSON format as follows:
        {
          "results": [
            {
              "username": "username1",
              "category": "Category",
              "confidence": 0.9
            },
            ...
          ]
        }
        
        Remember, use ONLY the categories provided in the list.
        """
        
        return prompt
    
    def _store_interest_results(self, user_id, results, category_mapping):
        """Store the interest analysis results in the database"""
        cursor = self.db_conn.cursor()
        
        # Process each result and update interests table
        for result in results:
            username = result.get("username")
            category = result.get("category")
            confidence = result.get("confidence", 0.5)
            
            # Skip if category doesn't match our predefined categories
            if category not in category_mapping:
                logger.warning(f"Category '{category}' for {username} not found in predefined categories")
                continue
            
            category_id = category_mapping[category]
            
            # Insert interest record
            cursor.execute("""
                INSERT INTO interests (user_id, category_id, confidence_score)
                VALUES (%s, %s, %s)
                ON CONFLICT (user_id, category_id) 
                DO UPDATE SET confidence_score = EXCLUDED.confidence_score, created_at = CURRENT_TIMESTAMP
            """, (user_id, category_id, confidence))
        
        self.db_conn.commit()
        logger.info(f"Stored {len(results)} interest results for user {user_id}")
    
    def process_pending_users(self):
        """Process users who have complete following data but no interest analysis"""
        try:
            cursor = self.db_conn.cursor()
            
            # Find users who have completed following data but no interest analysis
            cursor.execute("""
                SELECT u.username
                FROM users u
                JOIN scrape_jobs sj ON u.username = sj.target_username AND sj.job_type = 'following' AND sj.status = 'completed'
                LEFT JOIN interests i ON u.user_id = i.user_id
                WHERE i.id IS NULL
                LIMIT 5  -- Process 5 users at a time
            """)
            
            users = cursor.fetchall()
            
            if not users:
                logger.info("No pending users for interest analysis")
                return
            
            for user_row in users:
                username = user_row[0]
                logger.info(f"Processing interest analysis for user: {username}")
                self.analyze_user_interests(username)
                time.sleep(5)  # Add delay between users
            
            logger.info(f"Completed interest analysis for {len(users)} users")
            
        except Exception as e:
            logger.error(f"Error processing pending users for interest analysis: {str(e)}")
    
    def cleanup(self):
        """Clean up resources"""
        if self.db_conn:
            self.db_conn.close()