import requests
from bs4 import BeautifulSoup
import re

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8"
})

# Get paginated reviews page directly
url = 'https://www.degustapanama.com/panama/restaurante/casa-alejandro_101505_fecha_1_todos.html'
response = session.get(url, timeout=30)
print('Status:', response.status_code)
print('Content length:', len(response.content))

soup = BeautifulSoup(response.content, 'lxml')

# Find all review containers with various selectors
selectors = [
    '.review-item',
    '.review-card',
    '.comment-item',
    '.user-review',
    'div[class*="review"]',
    'article[class*="review"]',
    '.testimonial-item',
    '.review-entry'
]

found_any = False
for selector in selectors:
    elements = soup.select(selector)
    if elements:
        print(f'\nSelector "{selector}" found {len(elements)} elements')
        found_any = True
        for el in elements[:2]:
            text = el.get_text(strip=True)[:200]
            print(f'  Text: {text[:150]}...')

if not found_any:
    print('\nNo review containers found with common selectors')
    print('Looking at page structure...')

    # Find all divs with any kind of review-related class
    for div in soup.find_all('div'):
        cls = div.get('class', [])
        cls_str = ' '.join(cls).lower()
        if 'review' in cls_str or 'comment' in cls_str or 'user' in cls_str:
            text = div.get_text(strip=True)[:100]
            print(f'Class: {" ".join(cls)}')
            print(f'Text: {text[:80]}')
            print('---')

    # Print a section of the HTML to understand structure
    print('\n\nHTML preview of body:')
    body = soup.find('body')
    if body:
        print(body.prettify()[:3000])
