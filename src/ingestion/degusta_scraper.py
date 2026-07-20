"""
Web scraper for Degusta Panama restaurant reviews.
https://www.degustapanama.com/

Degusta renders its restaurant pages with schema.org microdata (itemprop
attributes), which carries far more than the visible HTML classes suggest:

    servesCuisine   -> real cuisine/category
    priceRange      -> real price range
    address         -> street address (zone can be derived from it)
    aggregateRating -> restaurant-level rating and review count
    review          -> the 5 most recent reviews, each with its own
                       reviewBody, author, ratingValue and datePublished

Everything below is read from those microdata attributes, so the scraper does
not depend on CSS class names (which change often and previously caused the
category/price/location fields to come back empty).

The site has no pagination on /panama/search, so restaurants are discovered by
combining several entry points: the city landing page plus one search query per
cuisine. That reaches ~220 distinct restaurants.
"""

import random
import re
import time
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.degustapanama.com"
SEARCH_URL = f"{BASE_URL}/panama/search"

# Search terms used to widen restaurant discovery beyond the landing page.
CUISINE_QUERIES = [
    "sushi", "italiana", "china", "mexicana", "peruana", "mariscos", "carnes",
    "pizza", "hamburguesa", "panamena", "espanola", "francesa", "vegetariana",
    "cafe", "postres", "arabe", "india", "tailandesa", "americana", "criolla",
    "asiatica", "argentina", "venezolana", "colombiana", "parrilla", "desayuno",
]

# Addresses end with the neighbourhood, sometimes followed by the city:
#   "Wanders and Yoo - Paitilla"                       -> "Paitilla"
#   "Calle 50 ..., Casa 1206 - Bella Vista - Panamá"   -> "Bella Vista"
CITY_TOKENS = {"panama", "panamá", "ciudad de panama", "ciudad de panamá"}


def get_session() -> requests.Session:
    """Create a requests session with browser-like headers."""
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    })
    return session


def get_page(session: requests.Session, url: str, delay: float = 1.5) -> Optional[BeautifulSoup]:
    """Fetch a page with rate limiting."""
    time.sleep(random.uniform(delay, delay * 1.5))
    try:
        response = session.get(url, timeout=30)
        response.raise_for_status()
        return BeautifulSoup(response.content, "lxml")
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None


def _itemprop(soup: BeautifulSoup, prop: str) -> Optional[str]:
    """Return the value of the first element carrying ``itemprop=prop``.

    Microdata values live either in a ``content`` attribute or in the element
    text, so both are checked.
    """
    el = soup.select_one(f'[itemprop="{prop}"]')
    if el is None:
        return None
    value = el.get("content") or el.get_text(" ", strip=True)
    value = (value or "").strip()
    return value or None


def _to_float(value: Optional[str]) -> Optional[float]:
    """Parse a rating/count string into a float, honouring a "K" suffix.

    Degusta writes large review counts as "1.9K", which must become 1900 rather
    than 1.9.
    """
    if not value:
        return None
    text = str(value)
    match = re.search(r"\d+(?:[.,]\d+)?", text)
    if not match:
        return None
    try:
        number = float(match.group(0).replace(",", "."))
    except ValueError:
        return None
    if re.match(r"\s*[kK]", text[match.end():]):
        number *= 1000
    return number


def _zone_from_address(address: str) -> Optional[str]:
    """Derive the neighbourhood from a Degusta address string."""
    parts = [p.strip() for p in address.split(" - ") if p.strip()]
    # Drop trailing city names so the neighbourhood is the last part left.
    while parts and parts[-1].lower() in CITY_TOKENS:
        parts.pop()
    if len(parts) < 2:
        return None
    return parts[-1]


def extract_aspect_ratings(soup: BeautifulSoup) -> Dict[str, float]:
    """Extract Degusta's own per-aspect scores (Comida / Servicio / Ambiente).

    These live in the ``.dg-reviews-stats`` block as "Comida 4.4 /5 Servicio
    4.5 /5 Ambiente 4.6 /5". The class must be matched exactly: a looser
    ``[class*="reviews-stats"]`` selector matches the section *title* first and
    returns no numbers at all.

    Having the site's own aspect scores is useful beyond reporting - they act as
    a reference to sanity-check the lexicon's aspect sentiment against.
    """
    section = soup.select_one(".dg-reviews-stats")
    if section is None:
        return {}

    text = section.get_text(" ", strip=True)
    ratings: Dict[str, float] = {}
    for aspect in ("Comida", "Servicio", "Ambiente"):
        match = re.search(rf"{aspect}\s*([\d]+(?:[.,]\d+)?)", text)
        if match:
            value = _to_float(match.group(1))
            if value is not None and 0 <= value <= 5:
                ratings[aspect.lower()] = value
    return ratings


def extract_restaurant_links(soup: BeautifulSoup) -> Dict[str, str]:
    """Map restaurant_id -> detail URL for every restaurant linked on a page."""
    found: Dict[str, str] = {}
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "/restaurante/" not in href or "reservar" in href or "agregar" in href:
            continue
        match = re.search(r"restaurante/[^_]+_(\d+)", href)
        if not match:
            continue
        restaurant_id = match.group(1)
        found.setdefault(restaurant_id, href if href.startswith("http") else BASE_URL + href)
    return found


def discover_restaurants(session: requests.Session, max_restaurants: int = 200,
                         delay: float = 1.5, verbose: bool = True) -> Dict[str, str]:
    """Discover restaurant detail URLs across several entry points.

    /panama/search has no pagination, so breadth comes from combining the city
    landing page with one search query per cuisine.
    """
    entry_points = [f"{BASE_URL}/panama", SEARCH_URL]
    entry_points += [f"{SEARCH_URL}?q={q}" for q in CUISINE_QUERIES]

    found: Dict[str, str] = {}
    for url in entry_points:
        if len(found) >= max_restaurants:
            break
        soup = get_page(session, url, delay)
        if soup is None:
            continue
        before = len(found)
        for rid, href in extract_restaurant_links(soup).items():
            found.setdefault(rid, href)
        if verbose:
            print(f"  {url.replace(BASE_URL, ''):45s} -> {len(found):3d} restaurantes "
                  f"(+{len(found) - before})")

    return dict(list(found.items())[:max_restaurants])


def get_restaurant_details(soup: BeautifulSoup, url: str, restaurant_id: str) -> Dict:
    """Extract restaurant-level metadata from a detail page's microdata."""
    details: Dict = {"restaurant_id": restaurant_id, "url": url}

    name_el = soup.find("h1")
    if name_el:
        details["restaurant_name"] = name_el.get_text(" ", strip=True)

    cuisine = _itemprop(soup, "servesCuisine")
    details["category"] = cuisine if cuisine else None

    price = _itemprop(soup, "priceRange")
    details["price_range"] = price if price else None

    # aggregateRating carries the restaurant's headline rating; the ratingValue
    # inside it is the first one on the page.
    agg = soup.select_one('[itemprop="aggregateRating"]')
    if agg is not None:
        details["overall_rating"] = _to_float(_itemprop(agg, "ratingValue"))
        details["review_count"] = _to_float(_itemprop(agg, "reviewCount"))

    # The site's own aspect scores, kept as reference values for the analysis.
    aspects = extract_aspect_ratings(soup)
    details["food_rating"] = aspects.get("comida")
    details["service_rating"] = aspects.get("servicio")
    details["ambiance_rating"] = aspects.get("ambiente")

    # Address -> street plus a derived zone (e.g. "Bella Vista").
    street = _itemprop(soup, "streetAddress") or _itemprop(soup, "address")
    if street:
        details["address"] = street
        zone = _zone_from_address(street)
        if not zone:
            region = _itemprop(soup, "addressRegion")
            zone = region.strip() if region else None
        details["location"] = zone
    else:
        details["location"] = None

    return details


def get_reviews_from_page(soup: BeautifulSoup) -> List[Dict]:
    """Extract the individual reviews embedded as schema.org microdata.

    Each review carries its own author, rating and publication date, so reviews
    are usable on their own rather than inheriting restaurant-level values.
    """
    reviews = []
    for rev in soup.select('[itemprop="review"]'):
        body = rev.select_one('[itemprop="reviewBody"]')
        if body is None:
            continue
        text = body.get_text(" ", strip=True)
        if len(text) < 10:
            continue

        author = rev.select_one('[itemprop="author"]')
        date = rev.select_one('[itemprop="datePublished"]')

        # The review's own score lives under its reviewRating subtree.
        rating_el = rev.select_one('[itemprop="reviewRating"] [itemprop="ratingValue"]') \
            or rev.select_one('[itemprop="ratingValue"]')
        rating_val = None
        if rating_el is not None:
            rating_val = _to_float(rating_el.get("content") or rating_el.get_text(strip=True))

        reviews.append({
            "review_text": text,
            "reviewer_name": author.get_text(" ", strip=True) if author else None,
            "review_rating": rating_val,
            "review_date": (date.get("content") or date.get_text(strip=True)) if date else None,
        })
    return reviews


def scrape_reviews_all(session: requests.Session, max_restaurants: int = 200,
                       delay: float = 1.5) -> pd.DataFrame:
    """Scrape restaurant pages and return a flat DataFrame of individual reviews."""
    print("Descubriendo restaurantes en Degusta...")
    restaurants = discover_restaurants(session, max_restaurants, delay)
    print(f"\n{len(restaurants)} restaurantes descubiertos. Extrayendo resenas...\n")

    rows = []
    for i, (rid, url) in enumerate(restaurants.items(), 1):
        print(f"[{i}/{len(restaurants)}] {rid}... ", end="", flush=True)

        page = get_page(session, url, delay)
        if page is None:
            print("FALLO")
            continue

        details = get_restaurant_details(page, url, rid)
        reviews = get_reviews_from_page(page)
        print(f"{str(details.get('restaurant_name'))[:30]:32s} -> {len(reviews)} resenas")

        for r in reviews:
            rows.append({
                "restaurant_id": f"dg_{rid}",
                "restaurant_name": details.get("restaurant_name"),
                "category": details.get("category"),
                "location": details.get("location"),
                "address": details.get("address"),
                "price_range": details.get("price_range"),
                # Restaurant-level rating, plus this review's own rating.
                "overall_rating": details.get("overall_rating"),
                "review_rating": r["review_rating"],
                # Degusta's own aspect scores for the restaurant (0-5).
                "food_rating": details.get("food_rating"),
                "service_rating": details.get("service_rating"),
                "ambiance_rating": details.get("ambiance_rating"),
                "review_text": r["review_text"],
                "review_date": r["review_date"],
                "reviewer_name": r["reviewer_name"],
                "source": "degusta",
            })

    return pd.DataFrame(rows)


def scrape_reviews_main(max_restaurants: int = 200, delay: float = 1.5) -> pd.DataFrame:
    """Scrape real Degusta reviews into data/raw/degusta_reviews.csv."""
    session = get_session()
    df = scrape_reviews_all(session, max_restaurants=max_restaurants, delay=delay)
    if df.empty:
        print("No se extrajo ninguna resena")
        return df

    Path("data/raw").mkdir(parents=True, exist_ok=True)
    df.to_csv("data/raw/degusta_reviews.csv", index=False)
    print(f"\nGuardadas {len(df)} resenas de {df['restaurant_id'].nunique()} restaurantes "
          f"en data/raw/degusta_reviews.csv")
    print(f"  con categoria: {df['category'].notna().sum()}/{len(df)}")
    print(f"  con precio:    {df['price_range'].notna().sum()}/{len(df)}")
    print(f"  con zona:      {df['location'].notna().sum()}/{len(df)}")
    print(f"  con rating:    {df['review_rating'].notna().sum()}/{len(df)}")
    return df


if __name__ == "__main__":
    scrape_reviews_main()
