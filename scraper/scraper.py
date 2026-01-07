import concurrent.futures
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse
import time
import threading

from .fetcher import Fetcher
from .parser import Parser
from .filters import ContentFilter
from .utils import is_valid_url, normalize_url, get_domain

class ScraperEngine:
    def __init__(self, base_url, config):
        self.base_url = base_url
        self.config = config
        
        # Configuration
        self.max_pages = int(config.get('max_pages', 10))
        self.max_depth = int(config.get('depth', 2))
        self.links_per_page = int(config.get('links_per_page', 5))
        
        self.domain = get_domain(base_url)
        self.visited_urls = set()
        self.visited_lock = threading.Lock()
        self.results = []
        
        self.fetcher = Fetcher()
        self.content_filter = ContentFilter(config.get('sections', {}))
        
        # Determine number of threads
        self.max_workers = 5

    def scrape_page(self, url, current_depth):
        """
        Scrapes a single page and returns extracted data and new links.
        """
        # Double check visited inside thread (though we check before submitting too)
        with self.visited_lock:
            if url in self.visited_urls:
                return None, []
            self.visited_urls.add(url)
        
        print(f"Scraping: {url} (Depth: {current_depth})")
        
        response = self.fetcher.fetch(url)
        if not response:
            return None, []
            
        soup = Parser.parse(response.text)
        if not soup:
            return None, []
            
        # Extract content
        data = self.content_filter.extract(soup, url)
        data['url'] = url
        
        # Extract links for next depth
        new_links = []
        if current_depth < self.max_depth:
            raw_links = Parser.extract_links(soup, url)
            count = 0
            for link in raw_links:
                if count >= self.links_per_page:
                    break
                    
                abs_link = normalize_url(url, link)
                if (abs_link and 
                    is_valid_url(abs_link) and 
                    get_domain(abs_link) == self.domain):
                    
                    # We don't check visited here to avoid lock contention, 
                    # we filter in the main loop or just let the set handle it
                    new_links.append(abs_link)
                    count += 1
                    
        return data, new_links

    def run(self):
        """
        Main execution method using ThreadPoolExecutor.
        """
        if not is_valid_url(self.base_url):
            return {"error": "Invalid Base URL"}

        # Queue of URLs to scrape: (url, depth)
        queue = [(self.base_url, 1)]
        self.results = []
        
        # Track scheduled URLs to avoid duplicates in queue
        scheduled_urls = {self.base_url}
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            while queue and len(self.visited_urls) < self.max_pages:
                # Prepare a batch of futures
                futures = {}
                
                # Take items from queue up to remaining capacity
                current_batch = []
                while queue and len(scheduled_urls) < self.max_pages + len(queue): # Approximate check
                    # We need to be careful not to over-schedule if we want to respect max_pages STRICTLY
                    # But for performance, slightly over-fetching is often okay. 
                    # Here we try to stick to the limit.
                    
                    if len(self.visited_urls) + len(current_batch) >= self.max_pages:
                        break
                        
                    url, depth = queue.pop(0)
                    
                    # Check if already visited (in case it was added by another batch, though scheduled_urls handles this)
                    with self.visited_lock:
                        if url in self.visited_urls:
                            continue

                    current_batch.append((url, depth))
                
                if not current_batch:
                    if not futures and not queue:
                         # No running tasks and no queue -> done
                         break
                    if not current_batch and futures:
                         # Wait for some futures to complete
                         pass
                    elif not current_batch and not futures:
                         break

                # Submit batch
                for url, depth in current_batch:
                    futures[executor.submit(self.scrape_page, url, depth)] = depth

                # Wait for this batch to finish (simplified generation-based BFS)
                # For true async, we'd add to queue as we go, but managing the pool is trickier.
                # Batch processing is safer for depth control.
                for future in concurrent.futures.as_completed(futures):
                    depth = futures[future]
                    try:
                        data, new_links = future.result()
                        if data:
                            self.results.append(data)
                        
                        # Add new links to queue if depth allows
                        if depth < self.max_depth:
                            for link in new_links:
                                if link not in scheduled_urls:
                                    scheduled_urls.add(link)
                                    queue.append((link, depth + 1))
                                    
                    except Exception as e:
                        print(f"Error processing future: {e}")
                
        return self.results
