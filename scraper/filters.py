from .utils import normalize_url, get_domain

class ContentFilter:
    """
    Extracts specific content from the BeautifulSoup object based on configuration.
    """
    
    def __init__(self, config: dict):
        """
        config: dict containing booleans for keys:
        - title
        - meta_description
        - headings
        - paragraphs
        - tables
        - links
        - images
        """
        self.config = config

    def extract(self, soup, url=None):
        if not soup:
            return {}

        data = {}

        if self.config.get('title'):
            # More robust title extraction
            if soup.title and soup.title.get_text(strip=True):
                raw_title = soup.title.get_text(" ", strip=True)
                data['title'] = " ".join(raw_title.split()) # Normalize whitespace
            else:
                # Fallback to h1 if title is missing
                h1 = soup.find('h1')
                if h1:
                    raw_h1 = h1.get_text(" ", strip=True)
                    data['title'] = " ".join(raw_h1.split())
                else:
                    data['title'] = "No Title"

        if self.config.get('meta_description'):
            # Handle variations of meta description
            description = ""
            # Priority 1: Standard meta description
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            if meta_desc and meta_desc.get('content'):
                description = meta_desc['content'].strip()
            
            # Priority 2: OG description (if standard is missing/empty)
            if not description:
                meta_og = soup.find('meta', attrs={'property': 'og:description'})
                if meta_og and meta_og.get('content'):
                    description = meta_og['content'].strip()
            
            # Priority 3: Twitter description
            if not description:
                meta_tw = soup.find('meta', attrs={'name': 'twitter:description'})
                if meta_tw and meta_tw.get('content'):
                    description = meta_tw['content'].strip()
            
            data['meta_description'] = description

        if self.config.get('headings'):
            # Get text from headings, removing nested tags if necessary but keeping text
            headings = []
            for h in soup.find_all(['h1', 'h2', 'h3']):
                text = h.get_text(" ", strip=True)
                if text:
                    headings.append(text)
            data['headings'] = headings

        if self.config.get('paragraphs'):
            # Extract paragraphs with better whitespace handling and filtering
            paragraphs = []
            for p in soup.find_all('p'):
                text = p.get_text(" ", strip=True)
                # Filter out empty or very short paragraphs (likely UI elements)
                if text and len(text) > 20:
                    paragraphs.append(text)
            data['paragraphs'] = paragraphs


        if self.config.get('tables'):
            tables = []
            for table in soup.find_all('table'):
                # Skip nested tables for cleaner output
                if table.find_parent('table'):
                    continue
                    
                table_data = {'headers': [], 'rows': []}
                
                # improved header extraction
                headers = []
                thead = table.find('thead')
                if thead:
                    headers = [th.get_text(" ", strip=True) for th in thead.find_all(['th', 'td'])]
                
                # If no thead, check first tr
                if not headers:
                    first_tr = table.find('tr')
                    if first_tr and (first_tr.find_all('th') or len(table.find_all('tr')) > 1):
                        # Treat first row as header if it has th or if table has multiple rows
                        headers = [cell.get_text(" ", strip=True) for cell in first_tr.find_all(['th', 'td'])]
                        # If we used the first row as header, we shouldn't process it as a body row (unless it was in thead)
                        # We'll handle this by iterating rows carefully below
                
                table_data['headers'] = headers
                
                # Extract rows
                rows = []
                # Get all trs
                all_trs = table.find_all('tr')
                
                # If we identified headers from the first tr and it wasn't in a thead, skip it in rows
                start_index = 0
                if headers and not thead and all_trs and all_trs[0].find_all(['th', 'td']):
                     # Check if the text matches the headers we extracted
                     first_row_text = [c.get_text(" ", strip=True) for c in all_trs[0].find_all(['th', 'td'])]
                     if first_row_text == headers:
                         start_index = 1

                for tr in all_trs[start_index:]:
                    # Skip if inside thead (already processed)
                    if tr.find_parent('thead'):
                        continue
                        
                    cells = [td.get_text(" ", strip=True) for td in tr.find_all(['td', 'th'])]
                    # Filter empty rows
                    if any(c for c in cells if c):
                        rows.append(cells)
                
                table_data['rows'] = rows
                
                # Quality check: only add tables with actual data
                if rows or (headers and len(headers) > 1):
                    tables.append(table_data)
            data['tables'] = tables

        if self.config.get('links'):
            # Extract link text, href, and categorize by context
            links = []
            seen_links = set()
            
            for a in soup.find_all('a', href=True):
                href = a['href']
                text = a.get_text(" ", strip=True)
                
                if not href or href.startswith(('#', 'javascript:')):
                    continue
                    
                # Normalize href
                if url:
                    href = normalize_url(url, href)
                    
                if not href or href in seen_links:
                    continue
                    
                seen_links.add(href)
                
                # Determine Context
                context = 'content'
                parent_tags = [p.name for p in a.parents]
                if 'nav' in parent_tags or 'header' in parent_tags:
                    context = 'nav'
                elif 'footer' in parent_tags:
                    context = 'footer'
                elif 'aside' in parent_tags or 'div' in parent_tags and any(cls in (a.find_parent('div').get('class') or []) for cls in ['sidebar', 'menu', 'widget']):
                    context = 'sidebar'
                
                link_type = 'external'
                if href.startswith('/') or (self.config.get('domain') and self.config['domain'] in href) or (url and get_domain(url) == get_domain(href)):
                    link_type = 'internal'
                elif href.startswith('mailto:'):
                    link_type = 'email'
                elif href.startswith('tel:'):
                    link_type = 'phone'
                    
                links.append({
                    'text': text or href,
                    'href': href,
                    'type': link_type,
                    'context': context
                })
            data['links'] = links

        if self.config.get('images'):
            images = []
            seen_src = set()
            
            for img in soup.find_all('img'):
                # Handle src, data-src, and srcset
                src = img.get('src') or img.get('data-src')
                srcset = img.get('srcset') or img.get('data-srcset')
                
                candidates = []
                
                if srcset:
                    # Parse srcset to get URLs
                    # srcset format: "url1 1x, url2 2x" or "url1 500w, url2 1000w"
                    parts = srcset.split(',')
                    for part in parts:
                        part = part.strip()
                        if not part: continue
                        
                        # Split by space to separate URL from descriptor
                        # Take the first part which is the URL
                        url_part = part.split()[0] if part else None
                        if url_part:
                            candidates.append(url_part)

                if src:
                    candidates.append(src)
                            
                # Find the best valid candidate
                final_src = None
                for candidate in candidates:
                    if not candidate or candidate.startswith('data:'):
                        continue
                        
                    # Normalize URL if base url is provided
                    abs_url = normalize_url(url, candidate) if url else candidate
                    
                    if abs_url and abs_url not in seen_src:
                        final_src = abs_url
                        break
                
                if not final_src:
                    continue
                    
                seen_src.add(final_src)
                
                alt = img.get('alt', '').strip()
                width = img.get('width')
                height = img.get('height')
                
                # Heuristic to filter small icons
                if width and width.isdigit() and int(width) < 20:
                    continue
                if height and height.isdigit() and int(height) < 20:
                    continue

                images.append({
                    'src': final_src,
                    'alt': alt or "Image",
                    'width': width,
                    'height': height
                })
            data['images'] = images

        return data
