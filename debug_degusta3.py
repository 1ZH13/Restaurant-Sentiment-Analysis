import requests
from bs4 import BeautifulSoup
import re

url = 'https://www.degustapanama.com/panama/search'
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8'
}

response = requests.get(url, headers=headers, timeout=30)
soup = BeautifulSoup(response.content, 'lxml')

# Get all restaurant detail links (not agregar-restaurante)
restaurant_pattern = re.compile(r'/panama/restaurante/[^/]+\.html')
restaurant_links = soup.find_all('a', href=restaurant_pattern)

print(f'Found {len(restaurant_links)} restaurant detail links')

# Get unique restaurant URLs
unique_urls = set()
for link in restaurant_links:
    href = link.get('href', '')
    if 'reservar' not in href and 'agregar' not in href:
        unique_urls.add(href)

print(f'Unique restaurant URLs: {len(unique_urls)}')

# Extract restaurant data from each link
restaurants = []
for href in list(unique_urls)[:5]:
    full_url = f'https://www.degustapanama.com{href}'
    print(f'\n{full_url}')

    # Get page for this restaurant
    resp = requests.get(full_url, headers=headers, timeout=30)
    soup2 = BeautifulSoup(resp.content, 'lxml')

    # Extract restaurant name
    title = soup2.find('h1')
    if title:
        print(f'  Name: {title.get_text(strip=True)}')

    # Extract rating
    rating_elem = soup2.select_one('[class*="rating"], .score, [class*="star"]')
    if rating_elem:
        print(f'  Rating element: {rating_elem.get_text(strip=True)}')

    # Look for review count
    reviews_elem = soup2.find(string=re.compile(r'reseñas|reviews?'))
    if reviews_elem:
        print(f'  Reviews: {reviews_elem.strip()}')

    # Look for category
    category_elems = soup2.select('[class*="category"], [class*="cuisine"], .tag')
    for c in category_elems[:2]:
        text = c.get_text(strip=True)
        if text and len(text) < 50:
            print(f'  Category: {text}')

    # Look for location
    location_elem = soup2.select_one('[class*="location"], [class*="address"], .zone')
    if location_elem:
        print(f'  Location: {location_elem.get_text(strip=True)}')
