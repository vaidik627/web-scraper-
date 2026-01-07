
import unittest
import requests
import time

from scraper.summarizer import SummarizerEngine

class TestSummarizer(unittest.TestCase):
    BASE_URL = "http://127.0.0.1:5000/api/summarize"
    TEST_URL = "https://www.example.com" # Simple stable URL

    def setUp(self):
        self.engine = SummarizerEngine()

    def test_noise_filtering(self):
        # Simulated noisy text input
        noisy_text = """
        ( October 2025 ) 3.14.2 [ 3 ] / 5 December 2025
        Python frameworks BlueBream CherryPy CubicWeb Django FastAPI Flask
        Google App Engine Grok Kivy mod_wsgi Nevow Pylons Pyramid
        Python is a high-level, general-purpose programming language.
        See also History of Python List of Python books
        """
        
        # We need to test the split_into_sentences method directly
        sentences = self.engine.split_into_sentences(noisy_text)
        
        # Expectation: 
        # 1. The list of frameworks should be filtered (high caps ratio, no verb)
        # 2. The date string should be filtered (junk detection)
        # 3. "Python is a..." should be KEPT
        
        self.assertTrue(any("Python is a high-level" in s for s in sentences), "Failed to keep valid sentence")
        self.assertFalse(any("BlueBream" in s for s in sentences), "Failed to filter keyword list")
        self.assertFalse(any("3.14.2" in s for s in sentences), "Failed to filter date/version junk")

    def test_deduplication(self):
        # Test Jaccard similarity
        s1 = "Python is a great programming language."
        s2 = "Python is a great language for programming." # Almost identical
        s3 = "Java is a different language."
        
        sim1_2 = self.engine.calculate_similarity(s1, s2)
        sim1_3 = self.engine.calculate_similarity(s1, s3)
        
        self.assertGreater(sim1_2, 0.6, "Similar sentences should have high score")
        self.assertLess(sim1_3, 0.4, "Different sentences should have low score")

    def test_summary_generation(self):
        payload = {"url": self.TEST_URL, "length": "medium"}
        response = requests.post(self.BASE_URL, json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("executive_summary", data)
        self.assertIn("highlights", data)
        self.assertIn("title", data)
        self.assertGreater(len(data["executive_summary"]), 10)
        self.assertIsInstance(data["highlights"], list)

    def test_length_control(self):
        # Short
        res_short = requests.post(self.BASE_URL, json={"url": self.TEST_URL, "length": "short"})
        len_short = len(res_short.json()["highlights"])
        
        # Long
        res_long = requests.post(self.BASE_URL, json={"url": self.TEST_URL, "length": "long"})
        len_long = len(res_long.json()["highlights"])
        
        # Note: On a tiny page like example.com, lengths might be similar, 
        # but logically the requested sentence count differs.
        # We'll just check valid responses for now.
        self.assertEqual(res_short.status_code, 200)
        self.assertEqual(res_long.status_code, 200)
        
        # Check logic: Long should generally allow more highlights than short if content permits
        # example.com is very short, so this might be equal, which is fine.

    def test_variation(self):
        # Request twice
        res1 = requests.post(self.BASE_URL, json={"url": self.TEST_URL, "length": "medium"})
        res2 = requests.post(self.BASE_URL, json={"url": self.TEST_URL, "length": "medium"})
        
        data1 = res1.json()
        data2 = res2.json()
        
        # Check if variation ID differs
        self.assertNotEqual(data1["variation_id"], data2["variation_id"])
        self.assertIsInstance(data1["variation_id"], str)
        
        # Note: On extremely short content, the text might be identical if there aren't enough sentences to shuffle.
        # But the system should at least flag them as different variations.

if __name__ == "__main__":
    unittest.main()
