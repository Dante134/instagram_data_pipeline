import time
import random
import requests
import json
import os
import datetime
from dotenv import load_dotenv
from fake_useragent import UserAgent
import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import instaloader

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("instagram_scraper.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("InstagramScraper")

class ProxyManager:
    def __init__(self):
        self.proxies = []
        self.current_index = 0
        # In a real implementation, you would load proxies from a service or file
        # For this example, we'll just simulate it
        self._load_proxies()
    
    def _load_proxies(self):
        # In a real implementation, you would:
        # 1. Connect to a proxy service API
        # 2. Load a list of residential proxies
        # Here we'll just use placeholders
        self.proxies = [
            {"http": "http://proxy1:port", "https": "https://proxy1:port"},
            {"http": "http://proxy2:port", "https": "https://proxy2:port"},
            # Add more proxies here
        ]
        random.shuffle(self.proxies)
    
    def get_proxy(self):
        if not self.proxies:
            return None
        
        proxy = self.proxies[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.proxies)
        return proxy

class InstagramScraper:
    def __init__(self, db_connection, use_proxies=True):
        load_dotenv()
        self.username = os.getenv('INSTAGRAM_USERNAME')
        self.password = os.getenv('INSTAGRAM_PASSWORD')
        self.db_conn = db_connection
        self.user_agent = UserAgent()
        self.session = requests.Session()
        self.proxy_manager = ProxyManager() if use_proxies else None
        self.last_request_time = time.time() - 10  # Initialize with offset
        self.insta_loader = None
        self.selenium_driver = None
    
    def _initialize_instaloader(self):
        if self.insta_loader is None:
            self.insta_loader = instaloader.Instaloader(
                download_pictures=False,
                download_videos=False,
                download_video_thumbnails=False,
                compress_json=False,
                download_geotags=False,
                post_metadata_txt_pattern='',
                max_connection_attempts=3
            )
            
            # Log in to Instagram
            try:
                self.insta_loader.login(self.username, self.password)
                logger.info("Successfully logged in with Instaloader")
            except Exception as e:
                logger.error(f"Failed to login with Instaloader: {str(e)}")
                raise
    
    def _initialize_selenium(self):
        if self.selenium_driver is None:
            options = Options()
            options.add_argument("--headless")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument(f"user-agent={self.user_agent.random}")
            
            # Add proxy if using
            if self.proxy_manager:
                proxy = self.proxy_manager.get_proxy()
                if proxy:
                    proxy_str = proxy['https'].replace('https://', '')
                    options.add_argument(f'--proxy-server={proxy_str}')
            
            self.selenium_driver = webdriver.Chrome(options=options)
            
            # Login to Instagram
            try:
                self.selenium_driver.get("https://www.instagram.com/accounts/login/")
                time.sleep(2 + random.random() * 2)  # Random delay
                
                # Enter username
                username_input = WebDriverWait(self.selenium_driver, 10).until(
                    EC.presence_of_element_located((By.NAME, "username"))
                )
                username_input.send_keys(self.username)
                
                # Enter password with human-like typing speed
                password_input = self.selenium_driver.find_element(By.NAME, "password")
                for char in self.password:
                    password_input.send_keys(char)
                    time.sleep(0.05 + random.random() * 0.1)
                
                # Click login button
                login_button = self.selenium_driver.find_element(By.XPATH, "//button[@type='submit']")
                login_button.click()
                
                # Wait for login to complete
                WebDriverWait(self.selenium_driver, 15).until(
                    EC.presence_of_element_located((By.XPATH, "//div[@role='dialog'] | //section[@main]"))
                )
                
                logger.info("Successfully logged in with Selenium")
                
                # Handle "Save Login Info" dialog if it appears
                try:
                    not_now_button = WebDriverWait(self.selenium_driver, 5).until(
                        EC.presence_of_element_located((By.XPATH, "//button[contains(text(), 'Not Now')]"))
                    )
                    not_now_button.click()
                except:
                    pass  # Dialog may not appear, so we can ignore this
                
            except Exception as e:
                logger.error(f"Failed to login with Selenium: {str(e)}")
                if self.selenium_driver:
                    self.selenium_driver.quit()
                    self.selenium_driver = None
                raise
    
    def _add_delay(self):
        """Add random delay to avoid detection"""
        elapsed = time.time() - self.last_request_time
        min_delay = 3  # Minimum delay in seconds
        
        if elapsed < min_delay:
            delay = min_delay - elapsed + (random.random() * 5)  # Add 0-5 random seconds
            logger.debug(f"Adding delay of {delay:.2f} seconds")
            time.sleep(delay)
        
        self.last_request_time = time.time()
    
    def _rotate_headers(self):
        """Create new headers with a different user agent"""
        return {
            'User-Agent': self.user_agent.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0',
        }
    
    def get_user_profile(self, username):
        """Get user profile information"""
        self._initialize_instaloader()
        self._add_delay()
        
        try:
            profile = instaloader.Profile.from_username(self.insta_loader.context, username)
            
            user_data = {
                "user_id": profile.userid,
                "username": profile.username,
                "full_name": profile.full_name,
                "bio": profile.biography,
                "profile_pic_url": profile.profile_pic_url,
                "follower_count": profile.followers,
                "following_count": profile.followees,
                "is_private": profile.is_private
            }
            
            # Save to database
            cursor = self.db_conn.cursor()
            cursor.execute("""
                INSERT INTO users 
                (user_id, username, full_name, bio, profile_pic_url, follower_count, following_count, is_private)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (user_id) 
                DO UPDATE SET 
                    username = EXCLUDED.username,
                    full_name = EXCLUDED.full_name,
                    bio = EXCLUDED.bio,
                    profile_pic_url = EXCLUDED.profile_pic_url,
                    follower_count = EXCLUDED.follower_count,
                    following_count = EXCLUDED.following_count,
                    is_private = EXCLUDED.is_private,
                    last_updated = CURRENT_TIMESTAMP
            """, (
                user_data["user_id"],
                user_data["username"],
                user_data["full_name"],
                user_data["bio"],
                user_data["profile_pic_url"],
                user_data["follower_count"],
                user_data["following_count"],
                user_data["is_private"]
            ))
            self.db_conn.commit()
            
            logger.info(f"Successfully retrieved and stored profile for {username}")
            return user_data
            
        except Exception as e:
            logger.error(f"Error getting profile for {username}: {str(e)}")
            raise
    
    def get_followers(self, username, max_count=None):
        """Get a user's followers with pagination and rate limiting"""
        self._initialize_instaloader()
        
        try:
            # Create scrape job entry
            cursor = self.db_conn.cursor()
            cursor.execute("""
                INSERT INTO scrape_jobs (target_username, job_type, status, started_at)
                VALUES (%s, %s, %s, %s)
                RETURNING job_id
            """, (username, 'followers', 'in_progress', datetime.datetime.now()))
            job_id = cursor.fetchone()[0]
            self.db_conn.commit()
            
            # Get profile
            profile = instaloader.Profile.from_username(self.insta_loader.context, username)
            user_id = profile.userid
            
            # Get followers
            follower_count = 0
            for follower in profile.get_followers():
                self._add_delay()  # Add delay between requests
                
                # First ensure follower exists in users table
                follower_data = {
                    "user_id": follower.userid,
                    "username": follower.username,
                    "full_name": follower.full_name,
                    "profile_pic_url": follower.profile_pic_url,
                    "is_private": follower.is_private
                }
                
                cursor.execute("""
                    INSERT INTO users 
                    (user_id, username, full_name, profile_pic_url, is_private)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (user_id) DO NOTHING
                """, (
                    follower_data["user_id"],
                    follower_data["username"],
                    follower_data["full_name"],
                    follower_data["profile_pic_url"],
                    follower_data["is_private"]
                ))
                
                # Then add follower relationship
                cursor.execute("""
                    INSERT INTO followers (user_id, follower_id)
                    VALUES (%s, %s)
                    ON CONFLICT (user_id, follower_id) DO NOTHING
                """, (user_id, follower.userid))
                
                follower_count += 1
                
                if follower_count % 10 == 0:
                    # Update progress and commit every 10 followers
                    cursor.execute("""
                        UPDATE scrape_jobs
                        SET processed_items = %s
                        WHERE job_id = %s
                    """, (follower_count, job_id))
                    self.db_conn.commit()
                
                if max_count and follower_count >= max_count:
                    break
            
            # Mark job as complete
            cursor.execute("""
                UPDATE scrape_jobs
                SET status = 'completed', 
                    completed_at = %s,
                    total_items = %s,
                    processed_items = %s
                WHERE job_id = %s
            """, (datetime.datetime.now(), follower_count, follower_count, job_id))
            self.db_conn.commit()
            
            logger.info(f"Successfully retrieved {follower_count} followers for {username}")
            
        except Exception as e:
            # Update job with error
            cursor.execute("""
                UPDATE scrape_jobs
                SET status = 'failed', 
                    error_message = %s
                WHERE job_id = %s
            """, (str(e), job_id))
            self.db_conn.commit()
            
            logger.error(f"Error getting followers for {username}: {str(e)}")
            raise
    
    def get_following(self, username, max_count=None):
        """Get accounts that a user follows with pagination and rate limiting"""
        self._initialize_instaloader()
        
        try:
            # Create scrape job entry
            cursor = self.db_conn.cursor()
            cursor.execute("""
                INSERT INTO scrape_jobs (target_username, job_type, status, started_at)
                VALUES (%s, %s, %s, %s)
                RETURNING job_id
            """, (username, 'following', 'in_progress', datetime.datetime.now()))
            job_id = cursor.fetchone()[0]
            self.db_conn.commit()
            
            # Get profile
            profile = instaloader.Profile.from_username(self.insta_loader.context, username)
            user_id = profile.userid
            
            # Get following
            following_count = 0
            for following in profile.get_followees():
                self._add_delay()  # Add delay between requests
                
                # First ensure following exists in users table
                following_data = {
                    "user_id": following.userid,
                    "username": following.username,
                    "full_name": following.full_name,
                    "profile_pic_url": following.profile_pic_url,
                    "is_private": following.is_private
                }
                
                cursor.execute("""
                    INSERT INTO users 
                    (user_id, username, full_name, profile_pic_url, is_private)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (user_id) DO NOTHING
                """, (
                    following_data["user_id"],
                    following_data["username"],
                    following_data["full_name"],
                    following_data["profile_pic_url"],
                    following_data["is_private"]
                ))
                
                # Then add following relationship
                cursor.execute("""
                    INSERT INTO following (user_id, following_id)
                    VALUES (%s, %s)
                    ON CONFLICT (user_id, following_id) DO NOTHING
                """, (user_id, following.userid))
                
                following_count += 1
                
                if following_count % 10 == 0:
                    # Update progress and commit every 10 following
                    cursor.execute("""
                        UPDATE scrape_jobs
                        SET processed_items = %s
                        WHERE job_id = %s
                    """, (following_count, job_id))
                    self.db_conn.commit()
                
                if max_count and following_count >= max_count:
                    break
            
            # Mark job as complete
            cursor.execute("""
                UPDATE scrape_jobs
                SET status = 'completed', 
                    completed_at = %s,
                    total_items = %s,
                    processed_items = %s
                WHERE job_id = %s
            """, (datetime.datetime.now(), following_count, following_count, job_id))
            self.db_conn.commit()
            
            logger.info(f"Successfully retrieved {following_count} following for {username}")
            
        except Exception as e:
            # Update job with error
            cursor.execute("""
                UPDATE scrape_jobs
                SET status = 'failed', 
                    error_message = %s
                WHERE job_id = %s
            """, (str(e), job_id))
            self.db_conn.commit()
            
            logger.error(f"Error getting following for {username}: {str(e)}")
            raise
    
    def calculate_mutual_followers(self, username):
        """Calculate and store mutual followers for a user"""
        try:
            cursor = self.db_conn.cursor()
            
            # Get user ID
            cursor.execute("SELECT user_id FROM users WHERE username = %s", (username,))
            result = cursor.fetchone()
            if not result:
                logger.error(f"User {username} not found in database")
                return
            
            user_id = result[0]
            
            # Calculate and store mutual followers
            cursor.execute("""
                INSERT INTO mutuals (user_id, mutual_id)
                SELECT f1.user_id, f1.follower_id
                FROM followers f1
                JOIN following f2 ON f1.user_id = f2.user_id AND f1.follower_id = f2.following_id
                WHERE f1.user_id = %s
                ON CONFLICT (user_id, mutual_id) DO NOTHING
            """, (user_id,))
            
            mutual_count = cursor.rowcount
            self.db_conn.commit()
            
            logger.info(f"Calculated {mutual_count} mutual followers for {username}")
            
        except Exception as e:
            logger.error(f"Error calculating mutual followers for {username}: {str(e)}")
            raise
    
    def cleanup(self):
        """Close all connections and clean up resources"""
        if self.selenium_driver:
            self.selenium_driver.quit()
        if self.session:
            self.session.close()