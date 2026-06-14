"""
Web scraper for RestaurantGuru - Panama City restaurants.
https://restaurantguru.com/Panama-City

RestaurantGuru aggregates real customer reviews (mostly from Google) and renders
the most recent ones server-side, so they can be retrieved with requests +
BeautifulSoup (no JavaScript / API key required). This is the project's second
data source, used because Tripadvisor returns HTTP 403 to scrapers.
"""

import json
import re
import time
import random
from pathlib import Path
from typing import Dict, List, Optional

import requests
from bs4 import BeautifulSoup
import pandas as pd

LIST_URL = "https://restaurantguru.com/Panama-City"
DETAIL_RE = re.compile(r"^https?://(?:[a-z]{2}\.)?restaurantguru\.com/[^/]+-Panama-City$")


def get_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    })
    return session


def get_page(session: requests.Session, url: str, delay: float = 4.0,
             retries: int = 3) -> Optional[BeautifulSoup]:
    """Fetch a page with rate limiting and exponential backoff on 429/503."""
    for attempt in range(retries):
        time.sleep(random.uniform(delay, delay * 1.5))
        try:
            resp = session.get(url, timeout=30)
            if resp.status_code in (429, 503):
                wait = delay * (2 ** attempt) + random.uniform(1, 3)
                print(f"(throttled {resp.status_code}, backoff {wait:.0f}s) ", end="", flush=True)
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return BeautifulSoup(resp.content, "lxml")
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            return None
    return None


def get_restaurant_links(soup: BeautifulSoup) -> List[str]:
    """Extract restaurant detail URLs from the Panama City listing page."""
    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if DETAIL_RE.match(href) and href.rstrip("/").split("/")[-1] != "Panama-City":
            links.append(href)
    # Deduplicate while preserving order
    seen, unique = set(), []
    for h in links:
        if h not in seen:
            seen.add(h)
            unique.append(h)
    return unique


def _parse_ldjson(soup: BeautifulSoup) -> Dict:
    """Pull restaurant metadata from any schema.org JSON-LD block."""
    meta: Dict = {}
    for tag in soup.find_all("script", attrs={"type": "application/ld+json"}):
        try:
            data = json.loads(tag.string or "")
        except (json.JSONDecodeError, TypeError):
            continue
        candidates = data if isinstance(data, list) else [data]
        for d in candidates:
            if not isinstance(d, dict):
                continue
            if d.get("name") and "name" not in meta:
                meta["name"] = d["name"]
            agg = d.get("aggregateRating")
            if isinstance(agg, dict) and agg.get("ratingValue") and "rating" not in meta:
                try:
                    meta["rating"] = float(agg["ratingValue"])
                except (TypeError, ValueError):
                    pass
            if d.get("priceRange") and "price_range" not in meta:
                meta["price_range"] = d["priceRange"]
            cuisine = d.get("servesCuisine")
            if cuisine and "category" not in meta:
                meta["category"] = ", ".join(cuisine) if isinstance(cuisine, list) else str(cuisine)
    return meta


def get_restaurant_data(soup: BeautifulSoup, url: str) -> Dict:
    """Extract restaurant metadata and its visible reviews from a detail page."""
    meta = _parse_ldjson(soup)

    name = meta.get("name")
    if not name:
        h1 = soup.find("h1")
        name = h1.get_text(" ", strip=True) if h1 else None

    # restaurant_id from the slug
    slug = url.rstrip("/").split("/")[-1]
    restaurant_id = f"rg_{abs(hash(slug)) % 10_000_000}"

    reviews = []
    for rev in soup.select(".o_review"):
        txt_el = rev.select_one(".text_full") or rev.select_one(".text_overflow") or rev.select_one(".text")
        if not txt_el:
            continue
        text = txt_el.get_text(" ", strip=True)
        if len(text) < 10:
            continue
        author = rev.select_one(".author_name, .name, [class*='author']")
        reviews.append({
            "review_text": text,
            "reviewer_name": author.get_text(" ", strip=True) if author else None,
        })

    return {
        "restaurant_id": restaurant_id,
        "restaurant_name": name,
        "category": meta.get("category", "General"),
        "location": "Panama City",
        "price_range": meta.get("price_range"),
        "overall_rating": meta.get("rating"),
        "reviews": reviews,
    }


def scrape_all(session: requests.Session, max_restaurants: int = 40, delay: float = 2.0) -> pd.DataFrame:
    """Scrape Panama City restaurants and return a flat DataFrame of reviews."""
    print("Fetching RestaurantGuru listing...")
    soup = get_page(session, LIST_URL, delay)
    if not soup:
        print("Failed to fetch listing page")
        return pd.DataFrame()

    links = get_restaurant_links(soup)
    print(f"Found {len(links)} restaurant URLs")

    rows = []
    for i, url in enumerate(links[:max_restaurants]):
        print(f"[{i+1}/{min(len(links), max_restaurants)}] {url.split('/')[-1][:40]}... ",
              end="", flush=True)
        page = get_page(session, url, delay)
        if not page:
            print("FAILED")
            continue
        data = get_restaurant_data(page, url)
        if not data["restaurant_name"] or not data["reviews"]:
            print("no reviews")
            continue
        print(f"{data['restaurant_name'][:28]} -> {len(data['reviews'])} reviews")
        for r in data["reviews"]:
            rows.append({
                "restaurant_id": data["restaurant_id"],
                "restaurant_name": data["restaurant_name"],
                "category": data["category"],
                "location": data["location"],
                "price_range": data["price_range"],
                "overall_rating": data["overall_rating"],
                "review_text": r["review_text"],
                "review_date": None,
                "reviewer_name": r["reviewer_name"],
                "source": "restaurantguru",
            })

    return pd.DataFrame(rows)


def main():
    session = get_session()
    df = scrape_all(session, max_restaurants=40, delay=2.0)
    if df.empty:
        print("No reviews scraped")
        return df
    Path("data/raw").mkdir(parents=True, exist_ok=True)
    df.to_csv("data/raw/restaurantguru_reviews.csv", index=False)
    print(f"\nSaved {len(df)} reviews from {df['restaurant_id'].nunique()} restaurants "
          f"to data/raw/restaurantguru_reviews.csv")
    return df


if __name__ == "__main__":
    main()
