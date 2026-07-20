"""
Web scraper for RestaurantGuru - Panama City restaurants.
https://restaurantguru.com/Panama-City

RestaurantGuru aggregates real customer reviews (mostly from Google) and renders
the most recent ones server-side, so they can be retrieved with requests +
BeautifulSoup (no JavaScript / API key required). This is the project's second
data source, used because Tripadvisor returns HTTP 403 to scrapers.

The site rate-limits aggressively (HTTP 503 after a handful of quick requests),
so every fetch goes through a patient exponential backoff. A full run is slow by
design; that is the cost of scraping this source politely.
"""

import hashlib
import json
import random
import re
import time
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
import requests
from bs4 import BeautifulSoup

LIST_URLS = [
    "https://restaurantguru.com/Panama-City",
    "https://restaurantguru.com/Panama-City-2",
]
DETAIL_RE = re.compile(r"^https?://(?:[a-z]{2}\.)?restaurantguru\.com/[^/]+-Panama-City$")

# "12 de marzo de 2025" / "March 12, 2025" / "2025-03-12"
DATE_ISO_RE = re.compile(r"\d{4}-\d{2}-\d{2}")


def get_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    })
    return session


def get_page(session: requests.Session, url: str, delay: float = 6.0,
             retries: int = 4) -> Optional[BeautifulSoup]:
    """Fetch a page with rate limiting and exponential backoff on 429/503.

    Unlike a plain retry loop this keeps widening the wait, because
    RestaurantGuru only lets go of a throttle after a sustained pause.
    """
    for attempt in range(retries):
        time.sleep(random.uniform(delay, delay * 1.4))
        try:
            resp = session.get(url, timeout=30)
            if resp.status_code in (429, 503):
                wait = delay * (2 ** attempt) + random.uniform(2, 6)
                print(f"(throttle {resp.status_code}, espera {wait:.0f}s) ", end="", flush=True)
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return BeautifulSoup(resp.content, "lxml")
        except requests.HTTPError as e:
            print(f"HTTP {e.response.status_code if e.response is not None else '?'} ", end="")
            return None
        except Exception as e:
            print(f"error {type(e).__name__} ", end="")
            return None
    return None


def make_restaurant_id(slug: str) -> str:
    """Build a stable restaurant id from the URL slug.

    Python's built-in ``hash()`` is randomised per process (PYTHONHASHSEED), so
    using it here previously produced different ids on every run, which broke
    deduplication across runs and any downstream join on restaurant_id.
    """
    digest = hashlib.md5(slug.encode("utf-8")).hexdigest()[:10]
    return f"rg_{digest}"


def get_restaurant_links(soup: BeautifulSoup) -> List[str]:
    """Extract restaurant detail URLs from a listing page."""
    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if DETAIL_RE.match(href) and href.rstrip("/").split("/")[-1] != "Panama-City":
            links.append(href)
    seen, unique = set(), []
    for h in links:
        if h not in seen:
            seen.add(h)
            unique.append(h)
    return unique


def discover_restaurants(session: requests.Session, delay: float = 6.0) -> List[str]:
    """Collect detail URLs across every listing page."""
    all_links: List[str] = []
    seen = set()
    for list_url in LIST_URLS:
        soup = get_page(session, list_url, delay)
        if soup is None:
            print(f"  {list_url} -> fallo")
            continue
        links = get_restaurant_links(soup)
        new = [h for h in links if h not in seen]
        seen.update(new)
        all_links.extend(new)
        print(f"  {list_url} -> {len(links)} enlaces ({len(new)} nuevos, acum {len(all_links)})")
    return all_links


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
            address = d.get("address")
            if isinstance(address, dict) and "location" not in meta:
                zone = address.get("addressLocality") or address.get("streetAddress")
                if zone:
                    meta["location"] = str(zone)
    return meta


def _review_date(review_el) -> Optional[str]:
    """Best-effort extraction of a review's publication date."""
    meta = review_el.select_one('meta[itemprop="datePublished"], time[datetime]')
    if meta is not None:
        value = meta.get("content") or meta.get("datetime")
        if value:
            return str(value)[:10]
    for el in review_el.select('[class*="date"], .time, time'):
        text = el.get_text(" ", strip=True)
        iso = DATE_ISO_RE.search(text)
        if iso:
            return iso.group(0)
        if text and len(text) <= 40:
            return text
    return None


def get_restaurant_data(soup: BeautifulSoup, url: str) -> Dict:
    """Extract restaurant metadata and its visible reviews from a detail page."""
    meta = _parse_ldjson(soup)

    name = meta.get("name")
    if not name:
        h1 = soup.find("h1")
        name = h1.get_text(" ", strip=True) if h1 else None

    slug = url.rstrip("/").split("/")[-1]

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
            "review_date": _review_date(rev),
        })

    return {
        "restaurant_id": make_restaurant_id(slug),
        "restaurant_name": name,
        "category": meta.get("category"),
        "location": meta.get("location"),
        "price_range": meta.get("price_range"),
        "overall_rating": meta.get("rating"),
        "reviews": reviews,
    }


def scrape_all(session: requests.Session, max_restaurants: int = 100,
               delay: float = 6.0, output_path: Optional[str] = None,
               save_every: int = 5) -> pd.DataFrame:
    """Scrape Panama City restaurants and return a flat DataFrame of reviews.

    Because this source throttles hard, a full run can take a long time and may
    need to be interrupted. When ``output_path`` is given the results are
    flushed to disk every few restaurants, so stopping the run keeps whatever
    was already collected instead of discarding all of it.
    """
    print("Descubriendo restaurantes en RestaurantGuru...")
    links = discover_restaurants(session, delay)
    links = links[:max_restaurants]
    print(f"\n{len(links)} fichas a visitar (con backoff por rate limiting)...\n")

    def _flush(collected: List[Dict]) -> None:
        if not output_path or not collected:
            return
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(collected).to_csv(output_path, index=False)

    rows: List[Dict] = []
    for i, url in enumerate(links, 1):
        print(f"[{i}/{len(links)}] {url.split('/')[-1][:40]:42s} ", end="", flush=True)
        page = get_page(session, url, delay)
        if page is None:
            print("FALLO")
            continue
        data = get_restaurant_data(page, url)
        if not data["restaurant_name"] or not data["reviews"]:
            print("sin resenas")
            continue
        print(f"{str(data['restaurant_name'])[:26]:28s} -> {len(data['reviews'])} resenas")
        for r in data["reviews"]:
            rows.append({
                "restaurant_id": data["restaurant_id"],
                "restaurant_name": data["restaurant_name"],
                "category": data["category"],
                "location": data["location"],
                "price_range": data["price_range"],
                "overall_rating": data["overall_rating"],
                "review_rating": None,   # RestaurantGuru does not expose per-review scores
                "review_text": r["review_text"],
                "review_date": r["review_date"],
                "reviewer_name": r["reviewer_name"],
                "source": "restaurantguru",
            })

        if i % save_every == 0:
            _flush(rows)

    _flush(rows)
    return pd.DataFrame(rows)


def main(max_restaurants: int = 100, delay: float = 6.0) -> pd.DataFrame:
    session = get_session()
    output = "data/raw/restaurantguru_reviews.csv"
    df = scrape_all(session, max_restaurants=max_restaurants, delay=delay,
                    output_path=output)
    if df.empty:
        print("No se extrajo ninguna resena")
        return df
    Path("data/raw").mkdir(parents=True, exist_ok=True)
    df.to_csv(output, index=False)
    print(f"\nGuardadas {len(df)} resenas de {df['restaurant_id'].nunique()} restaurantes "
          f"en data/raw/restaurantguru_reviews.csv")
    return df


if __name__ == "__main__":
    main()
