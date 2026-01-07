import re
from urllib.parse import urlparse, urljoin

def is_valid_url(url):
    """
    Checks if the URL is valid and belongs to the http/https scheme.
    """
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc]) and result.scheme in ['http', 'https']
    except ValueError:
        return False

def normalize_url(base_url, link):
    """
    Joins a relative link with the base URL to form an absolute URL.
    Removes fragments.
    """
    if not link:
        return None
    
    # Clean the link
    link = link.strip()
    
    # Handle fragments or javascript: links
    if link.startswith('#') or link.startswith('javascript:'):
        return None
        
    try:
        absolute_url = urljoin(base_url, link)
        # Remove fragment
        parsed = urlparse(absolute_url)
        return parsed._replace(fragment='').geturl()
    except Exception:
        return None

def get_domain(url):
    """
    Extracts the domain from a URL.
    """
    try:
        return urlparse(url).netloc
    except Exception:
        return ""
