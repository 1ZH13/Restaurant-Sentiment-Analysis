"""
Web scraper for Degusta Panama restaurant reviews.
https://www.degustapanama.com/

Note: Full review text is loaded via JavaScript. This scraper collects:
- Restaurant metadata (name, category, location, price)
- Overall rating and review count
- Aspect ratings (Comida, Servicio, Ambiente)
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import random
import re
from typing import List, Dict, Optional
from pathlib import Path
import os

BASE_URL = "https://www.degustapanama.com"
SEARCH_URL = f"{BASE_URL}/panama/search"


def get_session():
    """Create a requests session with proper headers."""
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
    })
    return session


def get_page(session, url: str, delay: float = 2.0) -> Optional[BeautifulSoup]:
    """Fetch a page with rate limiting."""
    time.sleep(random.uniform(delay, delay * 1.5))
    try:
        response = session.get(url, timeout=30)
        response.raise_for_status()
        return BeautifulSoup(response.content, "lxml")
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None


def get_restaurant_links_from_search(soup: BeautifulSoup) -> List[Dict]:
    """Extract restaurant links and basic info from search page."""
    restaurants = []

    for a in soup.find_all('a', href=True):
        href = a['href']
        if '/restaurante/' in href and 'reservar' not in href and 'agregar' not in href:
            # Extract restaurant info from the link and surrounding elements
            parent = a.find_parent(['div', 'li', 'article'])
            if parent:
                text = parent.get_text(strip=True)

                # Extract ID from URL
                match = re.search(r'restaurante/[^_]+_(\d+)', href)
                restaurant_id = match.group(1) if match else None

                if restaurant_id:
                    full_url = f"{BASE_URL}{href}" if href.startswith('/') else href

                    restaurants.append({
                        'restaurant_id': restaurant_id,
                        'url': full_url,
                        'raw_text': text[:200]
                    })

    # Deduplicate by restaurant_id
    seen = set()
    unique = []
    for r in restaurants:
        if r['restaurant_id'] not in seen:
            seen.add(r['restaurant_id'])
            unique.append(r)

    return unique


def get_restaurant_details(soup: BeautifulSoup, url: str, restaurant_id: str) -> Dict:
    """Extract detailed information from restaurant page."""
    details = {
        'restaurant_id': restaurant_id,
        'url': url
    }

    # Name
    name_elem = soup.find('h1')
    if name_elem:
        details['restaurant_name'] = name_elem.get_text(strip=True)

        # Overall rating
    rating_elem = soup.select_one('.reviews-badge, .reviews-data-badge, [class*="rating"]')
    if rating_elem:
        text = rating_elem.get_text(strip=True)
        # Clean text - remove extra spaces and normalize
        text = ' '.join(text.split())

        # Extract rating - first number that is valid (1-5)
        all_numbers = re.findall(r'[\d.]+', text)
        for num_str in all_numbers:
            try:
                val = float(num_str)
                if 1 <= val <= 5:
                    details['overall_rating'] = val
                    break
            except ValueError:
                continue

        # Extract review count - look for K suffix (e.g., "1.8Kreseñas")
        count_match = re.search(r'([\d.]+)\s*K\s*rese', text, re.IGNORECASE)
        if count_match:
            count_str = count_match.group(1)
            try:
                # Handle cases like "1.8" or "1"
                if '.' in count_str:
                    count_val = float(count_str)
                else:
                    count_val = float(count_str)
                details['review_count'] = int(count_val * 1000)
            except ValueError:
                pass

    # Aspect ratings (Comida, Servicio, Ambiente)
    aspect_ratings = {}
    ratings_section = soup.select_one('.dg-reviews-stats, .ratings-section, [class*="reviews-stats"]')
    if ratings_section:
        text = ratings_section.get_text(strip=True)
        # Parse "Comida4.8/5Servicio4.6/5Ambiente4.4/5"
        for match in re.finditer(r'(Comida|Servicio|Ambiente)\s*([\d.]+)', text):
            aspect = match.group(1).lower()
            rating = float(match.group(2))
            aspect_ratings[aspect] = rating

    if aspect_ratings:
        details['aspect_ratings'] = aspect_ratings
        if 'comida' in aspect_ratings:
            details['food_rating'] = aspect_ratings['comida']
        if 'servicio' in aspect_ratings:
            details['service_rating'] = aspect_ratings['servicio']
        if 'ambiente' in aspect_ratings:
            details['ambiance_rating'] = aspect_ratings['ambiente']

    # Category
    category_elems = soup.select('.categories a, [class*="category"] a, .cuisine-tags a')
    if category_elems:
        categories = [a.get_text(strip=True) for a in category_elems if a.get_text(strip=True)]
        if categories:
            details['category'] = ' / '.join(categories)
    else:
        # Try getting category from meta or other sources
        category_elem = soup.select_one('[class*="category"], .tag')
        if category_elem:
            details['category'] = category_elem.get_text(strip=True)

    # Location
    location_elem = soup.select_one('.location, [class*="location"], .address, .zone')
    if location_elem:
        details['location'] = location_elem.get_text(strip=True)

    # Price range
    price_elem = soup.select_one('.price, [class*="price-range"], .price_level')
    if price_elem:
        price_text = price_elem.get_text(strip=True)
        if '$' in price_text:
            details['price_range'] = price_text

    return details


def scrape_all(session, max_restaurants: int = 50, delay: float = 2.0) -> pd.DataFrame:
    """Main orchestrator - scrape restaurant data."""
    all_data = []

    # First, get restaurant list from search page
    print("Fetching restaurant list...")
    soup = get_page(session, SEARCH_URL, delay)
    if not soup:
        print("Failed to fetch search page")
        return pd.DataFrame()

    restaurant_links = get_restaurant_links_from_search(soup)
    print(f"Found {len(restaurant_links)} restaurant URLs")

    # Scrape each restaurant
    for i, rest in enumerate(restaurant_links[:max_restaurants]):
        print(f"\n[{i+1}/{min(len(restaurant_links), max_restaurants)}] {rest['restaurant_id']}... ", end="", flush=True)

        soup = get_page(session, rest['url'], delay)
        if not soup:
            print("FAILED")
            continue

        details = get_restaurant_details(soup, rest['url'], rest['restaurant_id'])
        details['source'] = 'degusta'

        print(f"OK - {details.get('restaurant_name', 'N/A')[:30]} | Rating: {details.get('overall_rating', 'N/A')}")

        all_data.append(details)

    # Convert to DataFrame
    if all_data:
        df = pd.DataFrame(all_data)
        return df
    else:
        return pd.DataFrame()


def save_to_csv(df: pd.DataFrame, path: str = "data/raw/degusta_restaurants.csv"):
    """Save scraped data to CSV."""
    if df.empty:
        print("No data to save")
        return

    Path(path).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    print(f"\nSaved {len(df)} restaurants to {path}")


def main():
    session = get_session()
    df = scrape_all(session, max_restaurants=50, delay=2.0)
    save_to_csv(df)

    if not df.empty:
        print("\nSample data:")
        print(df[['restaurant_name', 'overall_rating', 'category']].head())


if __name__ == "__main__":
    main()
