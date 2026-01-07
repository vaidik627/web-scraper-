import random
from .fetcher import Fetcher
from .parser import Parser
from collections import Counter
import re
import math

class SummarizerEngine:
    def __init__(self):
        self.fetcher = Fetcher()
        self.abbreviations = {'dr.', 'mr.', 'mrs.', 'ms.', 'jr.', 'sr.', 'e.g.', 'i.e.', 'vs.', 'ph.d.', 'u.s.', 'st.'}
        
        # Words that indicate a sentence is NOT suitable for a summary
        self.bad_start_words = {'but', 'and', 'or', 'because', 'so', 'however', 'therefore', 'moreover', 'also'}
        self.junk_phrases = {
            'click here', 'subscribe', 'sign up', 'log in', 'cookie policy', 'read more', 'learn more', 
            'all rights reserved', 'privacy policy', 'terms of service', 'skip to content', 'newsletter',
            'share this', 'follow us', 'advertisement', 'sponsored', 'related posts', 'leave a comment'
        }

    def split_into_sentences(self, text):
        """
        Smarter sentence splitting that handles common abbreviations.
        """
        # specialized splitting to avoid breaking on abbreviations
        # 1. Protect known abbreviations
        for abbr in self.abbreviations:
            text = text.replace(abbr, abbr.replace('.', '<PRD>'))
        
        # 2. Split by punctuation followed by space OR newlines
        sentences = re.split(r'(?<=[.!?])\s+|\n+', text)
        
        # 3. Restore abbreviations and clean
        clean_sentences = []
        for s in sentences:
            s = s.replace('<PRD>', '.')
            s = self.clean_sentence(s)
            if self.is_high_quality_sentence(s):
                clean_sentences.append(s)
                
        return clean_sentences

    def clean_sentence(self, text):
        # Remove citation markers like [1], [3]
        text = re.sub(r'\[\d+\]', '', text)
        # Remove leading special chars
        text = re.sub(r'^[\^•\-\*\|\>]\s*', '', text)
        # Remove multiple spaces
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        if not text: return ""
        
        # 1. Capitalize first letter
        if text[0].islower():
            text = text[0].upper() + text[1:]
            
        # 2. Ensure distinct ending punctuation
        if text[-1] not in '.!?':
            text += '.'
            
        return text

    def calculate_similarity(self, s1, s2):
        """Calculates similarity between two sentences."""
        # Remove punctuation for better word matching
        s1 = re.sub(r'[^\w\s]', '', s1)
        s2 = re.sub(r'[^\w\s]', '', s2)
        
        # Stopwords to ignore in similarity check
        stop = {'the', 'a', 'an', 'and', 'or', 'but', 'is', 'are', 'was', 'were', 'to', 'in', 'on', 'of', 'for', 'with', 'it', 'this', 'that'}
        
        set1 = {w for w in s1.lower().split() if w not in stop}
        set2 = {w for w in s2.lower().split() if w not in stop}
        
        if not set1 or not set2: return 0.0
        
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        
        if union == 0: return 0.0
        
        # Return standard Jaccard index for stability (0.0 to 1.0)
        return intersection / union

    def is_high_quality_sentence(self, text):
        lower_text = text.lower()
        words = text.split()
        
        # 1. Length check
        # Allow short sentences (4 words) if they are punchy, but filter very short nonsense
        if len(text) < 15 or len(words) < 4:
            return False
            
        # 2. Junk phrase detection
        if any(phrase in lower_text for phrase in self.junk_phrases):
            return False

        # 3. Bad start words (context-dependent words at start)
        first_word = words[0].lower().strip(',.')
        if first_word in self.bad_start_words:
            return False
            
        # 4. Link/List detection: High ratio of capitalized words
        cap_count = sum(1 for w in words if w[0].isupper())
        if len(words) > 6 and (cap_count / len(words)) > 0.6:
            return False 
            
        # 5. "Junk" detection (dates/versions/symbols only)
        if re.search(r'^[\d\s\Wa-zA-Z]{1,30}$', text): 
             return False
             
        # 6. Structure Check: Must contain at least one common "glue" word
        common_glue = {'the', 'a', 'an', 'to', 'of', 'in', 'on', 'is', 'are', 'was', 'with', 'for', 'and', 'or', 'as', 'by', 'at', 'from', 'it', 'this', 'that'}
        text_words = set(lower_text.split())
        if not any(w in text_words for w in common_glue):
             return False
             
        return True

    def text_rank_score(self, sentences):
        """
        Simplified TextRank algorithm.
        Constructs a graph where nodes are sentences and edges are similarity.
        """
        n = len(sentences)
        if n == 0: return []
        if n == 1: return [(1.0, 0, sentences[0])]

        # Build similarity matrix
        scores = [1.0] * n
        
        # Iterative scoring (PageRank-like)
        # We do a few iterations to propagate centrality
        for _ in range(3): 
            new_scores = [0.0] * n
            for i in range(n):
                for j in range(n):
                    if i == j: continue
                    sim = self.calculate_similarity(sentences[i], sentences[j])
                    if sim > 0:
                        new_scores[i] += sim * scores[j]
            
            # Normalize
            max_s = max(new_scores) if new_scores else 1
            if max_s > 0:
                scores = [s / max_s for s in new_scores]
        
        # Add position bias (Earlier sentences are usually more important)
        ranked_sentences = []
        for i, (score, sent) in enumerate(zip(scores, sentences)):
            final_score = score
            
            # Boost first sentence significantly (Topic Sentence)
            if i == 0: final_score *= 2.0
            # Boost first 20%
            elif i < n * 0.2: final_score *= 1.3
            
            # Boost numeric data slightly
            if re.search(r'\d+%|\$?\d+(?:,\d{3})*(?:\.\d+)?', sent):
                final_score *= 1.1
                
            ranked_sentences.append((final_score, i, sent))
            
        # Sort by score desc
        ranked_sentences.sort(key=lambda x: x[0], reverse=True)
        return ranked_sentences

    def generate_summary(self, url, length='medium'):
        response = self.fetcher.fetch(url)
        if not response:
            return {"error": "Failed to fetch URL"}

        soup = Parser.parse(response.text)
        if not soup:
            return {"error": "Failed to parse content"}

        # Extract Title
        title = "Untitled Page"
        if soup.title and soup.title.get_text(strip=True):
            title = soup.title.get_text(" ", strip=True)
        elif soup.find('h1'):
            title = soup.find('h1').get_text(" ", strip=True)

        # Extract Main Content
        # Exclude navigation, footer, sidebar explicitly
        for trash in soup.find_all(['nav', 'footer', 'aside', 'header', 'script', 'style', 'noscript', 'form', 'iframe']):
            trash.decompose()

        main_content = soup.find('main') or soup.find('article')
        
        if not main_content:
            # If no semantic tag, look for divs with content-related classes
            # Use "smart" selection: choose the div with the MOST text content
            candidates = soup.find_all('div', class_=re.compile(r'content|body|main'))
            if candidates:
                # Pick the one with the most text to avoid banner traps
                main_content = max(candidates, key=lambda t: len(t.get_text(strip=True)))
            else:
                main_content = soup.body

        paragraphs = []
        if main_content:
            for p in main_content.find_all(['p', 'div', 'section', 'li', 'h2', 'h3', 'h4']):
                # Only take direct text or text from paragraphs
                if p.name == 'div' and len(p.find_all('p')) > 0:
                    continue # Skip wrapper divs
                
                # Link Density Check
                text_length = len(p.get_text(strip=True))
                if text_length == 0: continue
                
                link_text_length = sum(len(a.get_text(strip=True)) for a in p.find_all('a'))
                if text_length > 0 and (link_text_length / text_length) > 0.5:
                    continue # Skip link-heavy blocks
                    
                text = p.get_text(" ", strip=True)
                
                # Strict filter for "list-like" garbage or menu items
                if len(text.split()) >= 4 and len(text) > 20: 
                    paragraphs.append(text)
        
        full_text = " ".join(paragraphs)
        
        # --- Image Fallback Strategy ---
        image_fallback = False
        image_captions = []
        
        if len(full_text) < 500: # Check for images if text is sparse
            images = soup.find_all('img')
            for img in images:
                alt = img.get('alt', '').strip()
                if alt and len(alt) > 10:
                    image_captions.append(alt)
            
            if image_captions:
                visual_summary = ". ".join(image_captions) + "."
                original_text_len = len(full_text)
                
                if original_text_len < 50: 
                     full_text = visual_summary
                     title = f"{title} (Visual Summary)"
                     image_fallback = True
                else:
                     full_text = full_text + " " + visual_summary
                     if original_text_len < 100:
                        image_fallback = True
            
            if not full_text:
                 return {"error": "No significant text or images found to summarize"}

        # Smart Sentence Tokenization
        sentences = self.split_into_sentences(full_text)
        
        if not sentences:
             return {"error": "Content too short to summarize"}

        # --- TextRank Scoring ---
        ranked_sentences = self.text_rank_score(sentences)

        # --- Output Structuring ---
        if length == 'short':
            exec_count = 1
            highlight_count = 3
        elif length == 'medium':
            exec_count = 2
            highlight_count = 5
        else: # long
            exec_count = 3
            highlight_count = 8

        # Strategy:
        # 1. Executive Summary: Combination of the 'Lead' sentence (context) and the 'Top' sentence (importance).
        # 2. Highlights: The next best sentences, sorted by occurrence.
        
        # Identify Lead Sentence (first valid sentence in original text)
        lead_sentence = sentences[0]
        
        # Identify Top Scored Sentence
        top_scored = ranked_sentences[0][2]
        
        exec_summary_list = []
        exec_summary_list.append(lead_sentence)
        
        if top_scored != lead_sentence and exec_count > 1:
             exec_summary_list.append(top_scored)
             
        # Dedup Executive Summary
        seen_exec = set()
        final_exec = []
        for s in exec_summary_list:
            if s not in seen_exec:
                final_exec.append(s)
                seen_exec.add(s)
        
        # Select Highlights
        highlights_list = []
        seen_highlights = set(final_exec)
        
        # Iterate through ranked sentences to find unique highlights
        for score, idx, sent in ranked_sentences:
            if len(highlights_list) >= highlight_count:
                break
                
            # Check duplication against existing highlights AND executive summary
            is_dup = False
            for seen in seen_highlights:
                if self.calculate_similarity(sent, seen) > 0.6:
                    is_dup = True
                    break
            
            if not is_dup:
                highlights_list.append((idx, sent))
                seen_highlights.add(sent)
        
        # Sort highlights by original index for narrative flow
        highlights_list.sort(key=lambda x: x[0])
        final_highlights = [h[1] for h in highlights_list]
        
        # Construct Output
        exec_text = " ".join(final_exec)
        
        # Formatting Variation
        variation_id = str(random.randint(100000, 999999))
        
        # Calculate stats
        original_word_count = len(full_text.split())
        summary_word_count = len(exec_text.split()) + sum(len(s.split()) for s in final_highlights)
        reduction_rate = int((1 - (summary_word_count / original_word_count)) * 100) if original_word_count > 0 else 0
        read_time = max(1, int(summary_word_count / 200)) 
        
        if image_fallback:
             exec_text = "[Visual Content Summary] " + exec_text

        return {
            "title": title,
            "executive_summary": exec_text,
            "highlights": final_highlights,
            "variation_id": variation_id,
            "stats": {
                "original_words": original_word_count,
                "summary_words": summary_word_count,
                "reduction_rate": f"{reduction_rate}%",
                "read_time": f"{read_time} min"
            }
        }
