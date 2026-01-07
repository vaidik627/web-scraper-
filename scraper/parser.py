from bs4 import BeautifulSoup

class Parser:
    """
    Parses HTML content using BeautifulSoup and lxml.
    """
    
    @staticmethod
    def parse(html_content):
        """
        Parses raw HTML string into a BeautifulSoup object.
        """
        if not html_content:
            return None
        
        try:
            return BeautifulSoup(html_content, 'lxml')
        except Exception as e:
            # Fallback to html.parser if lxml fails
            return BeautifulSoup(html_content, 'html.parser')

    @staticmethod
    def extract_links(soup, base_url):
        """
        Extracts all hrefs from the soup and normalizes them.
        """
        links = set()
        if not soup:
            return links
            
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            links.add(href)
            
        return links
