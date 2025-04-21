import random
import logging
import requests
import os
from instagram_pipeline.config import get_proxy_api_key

logger = logging.getLogger(__name__)

class ProxyManager:
    """Manages a pool of proxies for rotating IP addresses"""
    
    def __init__(self):
        self.proxies = []
        self.current_index = 0
        self.api_key = get_proxy_api_key()
        self._load_proxies()
    
    def _load_proxies(self):
        """Load proxies from a service or file"""
        # In a real implementation, you would connect to a proxy service API
        # This is a placeholder implementation
        
        try:
            if self.api_key:
                # Example of fetching from a proxy API service
                # response = requests.get(f"https://proxy-provider.com/api/proxies?api_key={self.api_key}")
                # if response.status_code == 200:
                #     self.proxies = response.json()["proxies"]
                pass
            
            # For demonstration purposes, we'll add some placeholder proxies
            # In a real implementation, these would come from your proxy service
            self.proxies = [
                {"http": "http://proxy1:port", "https": "https://proxy1:port"},
                {"http": "http://proxy2:port", "https": "https://proxy2:port"},
                {"http": "http://proxy3:port", "https": "https://proxy3:port"},
            ]
            
            random.shuffle(self.proxies)
            logger.info(f"Loaded {len(self.proxies)} proxies")
            
        except Exception as e:
            logger.error(f"Error loading proxies: {str(e)}")
            # Add some fallback proxies in case the service fails
            self.proxies = []
    
    def get_proxy(self):
        """Get the next proxy from the rotation"""
        if not self.proxies:
            logger.warning("No proxies available")
            return None
        
        proxy = self.proxies[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.proxies)
        return proxy
    
    def mark_proxy_failed(self, proxy):
        """Mark a proxy as failed and remove it from the pool"""
        if proxy in self.proxies:
            self.proxies.remove(proxy)
            logger.info(f"Removed failed proxy. {len(self.proxies)} proxies remaining")
            
            # If proxies are running low, try to reload
            if len(self.proxies) < 3:
                logger.info("Proxy pool running low, attempting to reload")
                self._load_proxies()