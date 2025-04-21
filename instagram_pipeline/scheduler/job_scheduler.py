import schedule
import time
import random
import psycopg2
import os
from dotenv import load_dotenv
import logging
from datetime import datetime, timedelta

# Import the scraper
from scraper.instagram_scraper import InstagramScraper

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("scheduler.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("JobScheduler")

class JobScheduler:
    def __init__(self):
        load_dotenv()
        self.db_conn = self._get_db_connection()
        self.scraper = InstagramScraper(self.db_conn)
        self.daily_quota = 200  # Maximum profiles to process per day
        self.current_day_processed = 0
        self.last_day = datetime.now().day
    
    def _get_db_connection(self):
        return psycopg2.connect(
            host=os.getenv('DB_HOST'),
            port=os.getenv('DB_PORT'),
            dbname=os.getenv('DB_NAME'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD')
        )
    
    def _reset_daily_counter(self):
        """Reset daily counter if it's a new day"""
        current_day = datetime.now().day
        if current_day != self.last_day:
            self.current_day_processed = 0
            self.last_day = current_day
    
    def schedule_user_scraping(self, username):
        """Add a user to the scraping queue"""
        try:
            cursor = self.db_conn.cursor()
            
            # Check if user is already in queue or completed recently
            cursor.execute("""
                SELECT status FROM scrape_jobs 
                WHERE target_username = %s AND job_type IN ('profile', 'followers', 'following') 
                AND started_at > %s
            """, (username, datetime.now() - timedelta(days=7)))
            
            recent_jobs = cursor.fetchall()
            
            if not recent_jobs:
                # Schedule jobs for this user
                for job_type in ['profile', 'followers', 'following']:
                    cursor.execute("""
                        INSERT INTO scrape_jobs (target_username, job_type, status)
                        VALUES (%s, %s, 'pending')
                    """, (username, job_type))
                
                self.db_conn.commit()
                logger.info(f"Scheduled scraping jobs for {username}")
            else:
                logger.info(f"User {username} already has recent jobs, skipping")
                
        except Exception as e:
            logger.error(f"Error scheduling user {username}: {str(e)}")
    
    def process_pending_jobs(self):
        """Process a batch of pending jobs"""
        self._reset_daily_counter()
        
        # Check if we've hit the daily quota
        if self.current_day_processed >= self.daily_quota:
            logger.info(f"Daily quota reached ({self.daily_quota}), skipping until tomorrow")
            return
        
        try:
            cursor = self.db_conn.cursor()
            
            # Get a batch of pending jobs
            remaining_quota = self.daily_quota - self.current_day_processed
            batch_size = min(remaining_quota, 10)  # Process max 10 jobs at a time
            
            cursor.execute("""
                SELECT job_id, target_username, job_type
                FROM scrape_jobs
                WHERE status = 'pending'
                ORDER BY job_id
                LIMIT %s
            """, (batch_size,))
            
            jobs = cursor.fetchall()
            
            if not jobs:
                logger.info("No pending jobs found")
                return
            
            for job_id, username, job_type in jobs:
                try:
                    # Add a random delay between jobs
                    time.sleep(random.uniform(5, 15))
                    
                    logger.info(f"Processing job {job_id}: {job_type} for {username}")
                    
                    # Process the job based on type
                    if job_type == 'profile':
                        self.scraper.get_user_profile(username)
                    elif job_type == 'followers':
                        self.scraper.get_followers(username)
                    elif job_type == 'following':
                        self.scraper.get_following(username)
                    
                    # If we've processed both followers and following, calculate mutuals
                    if job_type in ['followers', 'following']:
                        cursor.execute("""
                            SELECT COUNT(*) FROM scrape_jobs
                            WHERE target_username = %s 
                            AND job_type IN ('followers', 'following')
                            AND status = 'completed'
                        """, (username,))
                        
                        completed_count = cursor.fetchone()[0]
                        
                        if completed_count == 2:  # Both followers and following are done
                            self.scraper.calculate_mutual_followers(username)
                    
                    self.current_day_processed += 1
                    
                except Exception as e:
                    logger.error(f"Error processing job {job_id}: {str(e)}")
                    
                    # Update job status to failed
                    cursor.execute("""
                        UPDATE scrape_jobs
                        SET status = 'failed', error_message = %s
                        WHERE job_id = %s
                    """, (str(e), job_id))
                    self.db_conn.commit()
            
            logger.info(f"Processed {len(jobs)} jobs. Daily total: {self.current_day_processed}/{self.daily_quota}")
            
        except Exception as e:
            logger.error(f"Error in job processing: {str(e)}")
    
    def run_scheduler(self):
        """Run the scheduler with defined intervals"""
        # Process jobs every 30 minutes
        schedule.every(30).minutes.do(self.process_pending_jobs)
        
        # Run the scheduler loop
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    
    def cleanup(self):
        """Clean up resources"""
        if self.scraper:
            self.scraper.cleanup()
        if self.db_conn:
            self.db_conn.close()

if __name__ == "__main__":
    scheduler = JobScheduler()
    try:
        # Add some initial users to scrape
        scheduler.schedule_user_scraping("instagram")  # Example user
        
        # Start the scheduler
        scheduler.run_scheduler()
    except KeyboardInterrupt:
        logger.info("Scheduler stopped by user")
    finally:
        scheduler.cleanup()