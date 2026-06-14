import requests
from bs4 import BeautifulSoup

url = 'https://www.degustapanama.com/panama/search'
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8'
}

response = requests.get(url, headers=headers, timeout=30)
soup = BeautifulSoup(response.content, 'lxml')

# Look for restaurant cards
print('Looking for restaurant cards...')

# Try different selectors
selectors_to_try = [
    ('div', {'class': 'restaurant-card'}),
    ('div', {'class': 'place-card'}),
    ('a', {'href': lambda x: x and 'restaurante' in x}),
    ('div', {'class': 'col'}),
]

for tag, attrs in selectors_to_try:
    elements = soup.find_all(tag, attrs)
    if elements:
        print(f'Found {len(elements)} elements with tag={tag}, attrs={attrs}')
        # Print first element structure
        if elements[0]:
            print('First element preview:')
            print(elements[0].prettify()[:500])
            print('---')

# Find all divs with col- classes
cols = soup.find_all('div', class_=lambda x: x and 'col' in str(x).lower())
print(f'\nDivs with col in class: {len(cols)}')
for c in cols[:3]:
    print(c.get('class'))
    print(c.prettify()[:300])
    print('---')
