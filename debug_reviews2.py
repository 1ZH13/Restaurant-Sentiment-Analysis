import requests
from bs4 import BeautifulSoup
import re

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8"
})

# First get main page
url = 'https://www.degustapanama.com/panama/restaurante/casa-alejandro_101505.html'
response = session.get(url, timeout=30)
soup = BeautifulSoup(response.content, 'lxml')

# Find all review-related divs
print('Looking for review structures...')

# Get all divs with class containing review
for div in soup.find_all('div'):
    cls = div.get('class', [])
    cls_str = ' '.join(cls)
    if 'review' in cls_str.lower():
        text = div.get_text(strip=True)[:100]
        print(f'Class: {cls_str}')
        print(f'Text: {text[:80]}')
        print('---')

# Look for the actual reviews
print('\n\nLooking for user reviews...')
# Common patterns for user reviews
for pattern in ['user-review', 'user_review', 'client-review', 'visitor-review']:
    found = soup.find_all(class_=re.compile(pattern, re.I))
    if found:
        print(f'Found {len(found)} elements with class containing {pattern}')
