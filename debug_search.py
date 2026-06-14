import requests
from bs4 import BeautifulSoup
import re
import time
import random

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8"
})

BASE_URL = "https://www.degustapanama.com"

# Try different search URLs
search_urls = [
    f"{BASE_URL}/panama/search",
    f"{BASE_URL}/panama/search?sort=recent",
    f"{BASE_URL}/panama/search?sort=rating",
]

all_restaurants = set()

for search_url in search_urls:
    print(f"\nTrying: {search_url}")
    response = session.get(search_url, timeout=30)
    print(f"Status: {response.status_code}")

    soup = BeautifulSoup(response.content, 'lxml')

    # Get all restaurant URLs
    for a in soup.find_all('a', href=True):
        href = a['href']
        if '/restaurante/' in href and 'reservar' not in href and 'agregar' not in href:
            match = re.search(r'restaurante/[^_]+_(\d+)', href)
            if match:
                rest_id = match.group(1)
                full_url = f"{BASE_URL}{href}" if href.startswith('/') else href
                all_restaurants.add((rest_id, full_url))

    time.sleep(1)

print(f"\nTotal unique restaurants found: {len(all_restaurants)}")

# Check for pagination
print("\nChecking for pagination...")
soup = BeautifulSoup(response.content, 'lxml')

# Look for pagination links
for a in soup.find_all('a', href=True):
    if 'page' in a['href'].lower() or 'pagina' in a['href'].lower():
        print(f"Pagination link: {a['href']}")

# Print first few restaurants
print("\nFirst 10 restaurants:")
for rest_id, url in list(all_restaurants)[:10]:
    print(f"  {rest_id}: {url}")
