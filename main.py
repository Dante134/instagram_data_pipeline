import os
import logging
import time
import argparse
import psycopg2
from dotenv import load_dotenv

# Import our modules
from instagram_pipeline.database.setup import create_database, create_tables
from instagram_pipeline.scraper.instagram_scraper import InstagramScraper
from instagram_pipeline.scheduler.job_scheduler import JobScheduler
from instagram_pipeline.analysis.interest_analyzer import InterestAnalyzer
r

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("instagram_pipeline.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("InstagramPipeline")

class InstagramPipeline:
    def __init__(self):
        load_dotenv()
        # Initialize database
        create_database()
        create_tables()
        
        # Get database connection
        self.db_conn = self._get_db_connection()
        
        # Initialize components
        self.scraper = InstagramScraper(self.db_conn)
        self.scheduler = JobScheduler()
        self.analyzer = InterestAnalyzer()
    
    def _get_db_connection(self):
        return psycopg2.connect(
            host=os.getenv('DB_HOST'),
            port=os.getenv('DB_PORT'),
            dbname=os.getenv('DB_NAME'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD')
        )
    
    def add_target_user(self, username):
        """Add a target user to scrape"""
        logger.info(f"Adding target user: {username}")
        self.scheduler.schedule_user_scraping(username)
    
    def run_manual_scrape(self, username):
        """Run manual scrape for a specific user"""
        logger.info(f"Running manual scrape for user: {username}")
        
        try:
            # 1. Get user profile
            self.scraper.get_user_profile(username)
            logger.info(f"Profile for {username} scraped successfully")
            
            # 2. Get followers
            self.scraper.get_followers(username)
            logger.info(f"Followers for {username} scraped successfully")
            
            # 3. Get following
            self.scraper.get_following(username)
            logger.info(f"Following for {username} scraped successfully")
            
            # 4. Calculate mutual followers
            self.scraper.calculate_mutual_followers(username)
            logger.info(f"Mutual followers for {username} calculated successfully")
            
            # 5. Analyze interests
            self.analyzer.analyze_user_interests(username)
            logger.info(f"Interest analysis for {username} completed successfully")
            
            return True
        except Exception as e:
            logger.error(f"Error during manual scrape for {username}: {str(e)}")
            return False
    
    def run_scheduled_pipeline(self):
        """Run the scheduled pipeline continuously"""
        logger.info("Starting scheduled pipeline")
        
        try:
            # Add your initial target users here
            initial_users = ["instagram", "techcrunch", "nationalgeographic"]  # Example users
            for username in initial_users:
                self.add_target_user(username)
            
            # Start the scheduler's job loop
            self.scheduler.run_scheduler()
            
        except KeyboardInterrupt:
            logger.info("Pipeline stopped by user")
        except Exception as e:
            logger.error(f"Error in scheduled pipeline: {str(e)}")
    
    def run_interest_analysis_only(self):
        """Run interest analysis for pending users"""
        logger.info("Starting interest analysis for pending users")
        
        try:
            while True:
                self.analyzer.process_pending_users()
                logger.info("Waiting for next batch of users...")
                time.sleep(300)  # Check every 5 minutes
                
        except KeyboardInterrupt:
            logger.info("Interest analysis stopped by user")
        except Exception as e:
            logger.error(f"Error in interest analysis: {str(e)}")
    
    def cleanup(self):
        """Clean up all resources"""
        if self.scraper:
            self.scraper.cleanup()
        if self.scheduler:
            self.scheduler.cleanup()
        if self.analyzer:
            self.analyzer.cleanup()
        if self.db_conn:
            self.db_conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Instagram Data Pipeline")
    parser.add_argument("--mode", choices=["scheduled", "manual", "analysis"], default="scheduled",
                        help="Pipeline mode: scheduled, manual, or analysis only")
    parser.add_argument("--username", help="Username for manual mode")
    
    args = parser.parse_args()
    
    pipeline = InstagramPipeline()
    
    try:
        if args.mode == "scheduled":
            pipeline.run_scheduled_pipeline()
        elif args.mode == "manual":
            if not args.username:
                print("Error: Username required for manual mode")
                parser.print_help()
                exit(1)
            pipeline.run_manual_scrape(args.username)
        elif args.mode == "analysis":
            pipeline.run_interest_analysis_only()
    finally:
        pipeline.cleanup()