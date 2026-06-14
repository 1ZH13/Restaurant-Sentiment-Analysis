import requests
from bs4 import BeautifulSoup

url = 'https://www.degustapanama.com/panama/search'
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8'
}

response = requests.get(url, headers=headers, timeout=30)
print('Status:', response.status_code)
print('Content length:', len(response.content))

soup = BeautifulSoup(response.content, 'lxml')

# Find all links
links = soup.find_all('a')
print('Total links:', len(links))

# Find links that might be restaurants
restaurant_links = [l for l in links if 'restaurante' in str(l.get('href', ''))]
print('Restaurant links found:', len(restaurant_links))

for l in restaurant_links[:10]:
    href = l.get('href', '')
    text = l.get_text(strip=True)[:80]
    print('  -', href[:80])
    print('    Text:', text)
