import requests
from bs4 import BeautifulSoup
import re

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8"
})

url = 'https://www.degustapanama.com/panama/restaurante/casa-alejandro_101505.html'
response = session.get(url, timeout=30)
soup = BeautifulSoup(response.content, 'lxml')

# Look for pagination links
print('Looking for pagination...')

# Check for review section
reviews_section = soup.select_one('#comentarios, .reviews-section, [id*="review"]')
if reviews_section:
    print('Found reviews section')
    print(reviews_section.prettify()[:1000])

# Look for all links with fecha or page
links = soup.find_all('a', href=True)
for link in links:
    href = link['href']
    if 'fecha' in href or 'page' in href.lower() or 'review' in href.lower():
        print('Pagination link:', href)

# Look for the reviews container
print('\n\nLooking for review containers...')
review_containers = soup.select('.review-container, .comment, [class*="review"]')
print(f'Found {len(review_containers)} review containers')

# Print first few reviews
for i, container in enumerate(review_containers[:2]):
    print(f'\n--- Review {i+1} ---')
    print(container.get_text(strip=True)[:300])
