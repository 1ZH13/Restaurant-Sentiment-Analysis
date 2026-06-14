"""
Web scraper for Tripadvisor Panama restaurant reviews.
https://www.tripadvisor.com/Restaurants-g294480-Panama_City_Panama_Province.html
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import random
import re
from typing import List, Dict, Optional
from pathlib import Path

GEO_ID = "g294480"
BASE_URL = "https://www.tripadvisor.com"
RESTAURANTS_URL = f"{BASE_URL}/Restaurants-{GEO_ID}-Panama_City_Panama_Province.html"


class TripadvisorScraper:
    def __init__(self, delay_seconds: float = 5.0):
        self.delay_seconds = delay_seconds
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
        })

    def _get_page(self, url: str) -> Optional[BeautifulSoup]:
        """Fetch a page with rate limiting."""
        time.sleep(random.uniform(self.delay_seconds, self.delay_seconds * 1.5))
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return BeautifulSoup(response.content, "lxml")
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            return None

    def _extract_restaurant_id(self, link: str) -> Optional[str]:
        """Extract restaurant ID from detail page URL."""
        match = re.search(r"-d(\d+)-Reviews-", link)
        return match.group(1) if match else None

    def _parse_rating(self, rating_text: str) -> Optional[float]:
        """Parse rating from bubble text like '4.5 of 5 bubbles'."""
        match = re.search(r"(\d+\.?\d*)", rating_text)
        return float(match.group(1)) if match else None

    def _parse_price_range(self, price_text: str) -> str:
        """Parse price range from text like '$$ - $$$' or '$$$$'."""
        return price_text.strip() if price_text else ""

    def get_restaurant_list(self, offset: int = 0, per_page: int = 30) -> List[Dict]:
        """Extract list of restaurants from main page with pagination."""
        url = f"{RESTAURANTS_URL}?ajax=1&sort=recommended&seeMore=1&since={offset}"
        if offset > 0:
            url = f"{RESTAURANTS_URL}?skipaka=1&start={offset}"

        soup = self._get_page(url)
        if not soup:
            return []

        restaurants = []

        # Try different selectors for restaurant cards
        cards = soup.select(
            "div[data-test-target='restaurants-list'] a, "
            ".restaurants-list a, "
            "div.LwqMD a, "
            "a[href*='Restaurant_Review']"
        )

        for card in cards:
            try:
                # Get name
                name_elem = card.select_one("h3, [data-test-target='title'], .restaurants-list .title")
                if not name_elem:
                    continue

                # Get link
                href = card.get("href", "")
                if "Restaurant_Review" not in href:
                    continue

                detail_url = f"{BASE_URL}{href}" if href.startswith("/") else href

                # Get rating
                rating_elem = card.select_one("[class*='bubble'], .rating .ui_bubble_rating")
                rating = None
                if rating_elem:
                    rating_class = rating_elem.get("class", [])
                    for cls in rating_class:
                        match = re.search(r"bubble_(\d+)", cls)
                        if match:
                            rating = int(match.group(1)) / 10
                            break

                # Get reviews count
                reviews_elem = card.select_one("span[class*='review'], .review-count")
                reviews_text = reviews_elem.text.strip() if reviews_elem else "0 reviews"
                reviews_count = int(re.search(r"([\d,]+)", reviews_text.replace(",", "")).group(1)) if re.search(r"([\d,]+)", reviews_text) else 0

                # Get category
                category_elem = card.select_one("[class*='cuisine'], .cuisine")
                category = category_elem.text.strip() if category_elem else ""

                # Get price range
                price_elem = card.select_one("[class*='price'], .price")
                price_range = self._parse_price_range(price_elem.text) if price_elem else ""

                restaurants.append({
                    "restaurant_id": self._extract_restaurant_id(href),
                    "name": name_elem.text.strip(),
                    "rating": rating,
                    "reviews_count": reviews_count,
                    "category": category,
                    "price_range": price_range,
                    "detail_url": detail_url
                })
            except Exception as e:
                print(f"Error parsing card: {e}")
                continue

        return restaurants

    def get_restaurant_details(self, restaurant_id: str) -> Dict:
        """Extract detailed information from restaurant page."""
        url = f"{BASE_URL}/Restaurant_Review-{GEO_ID}-d{restaurant_id}-Reviews-Panama_City_Panama_Province.html"

        soup = self._get_page(url)
        if not soup:
            return {}

        details = {}

        # Name
        name_elem = soup.select_one("h1[data-test-target='top-info-header'], .restaurant-name")
        details["name"] = name_elem.text.strip() if name_elem else ""

        # Overall rating
        rating_elem = soup.select_one(".ui_bubble_rating, [class*='bubble_']")
        if rating_elem:
            rating_class = rating_elem.get("class", [])
            for cls in rating_class:
                match = re.search(r"bubble_(\d+)", cls)
                if match:
                    details["overall_rating"] = int(match.group(1)) / 10
                    break

        # Reviews count
        reviews_elem = soup.select_one(".reviews_count, [data-test-target='reviews-count']")
        if reviews_elem:
            reviews_text = reviews_elem.text.strip()
            details["reviews_count"] = int(re.search(r"([\d,]+)", reviews_text.replace(",", "")).group(1)) if re.search(r"([\d,]+)", reviews_text) else 0

        # Category
        category_elem = soup.select_one(".cuisine, [data-test-target='restaurant-category']")
        if category_elem:
            details["category"] = category_elem.text.strip()

        # Price range
        price_elem = soup.select_one(".price, .price_level")
        if price_elem:
            details["price_range"] = self._parse_price_range(price_elem.text)

        # Location
        location_elem = soup.select_one(".address, .address_string")
        if location_elem:
            details["location"] = location_elem.text.strip()

        # Description/excerpts
        details["highlights"] = []
        highlight_elems = soup.select(".quote, .highlight, .review-highlight")
        for elem in highlight_elems[:3]:
            details["highlights"].append(elem.text.strip())

        return details

    def get_restaurant_reviews(self, restaurant_id: str, offset: int = 0, per_page: int = 10) -> List[Dict]:
        """Extract reviews for a restaurant with pagination."""
        url = f"{BASE_URL}/Restaurant_Review-{GEO_ID}-d{restaurant_id}-Reviews-Panama_City_Panama_Province.html"
        if offset > 0:
            url = f"{BASE_URL}/Restaurant_Review-{GEO_ID}-d{restaurant_id}-Reviews-or{offset}-Panama_City_Panama_Province.html"

        soup = self._get_page(url)
        if not soup:
            return []

        reviews = []
        review_containers = soup.select(".review-container, .review, div[data-test-target='reviews-list'] > div")

        for container in review_containers:
            try:
                review = {
                    "restaurant_id": restaurant_id,
                    "reviewer_name": "",
                    "review_date": "",
                    "review_text": "",
                    "rating": None,
                    "title": ""
                }

                # Review ID
                review["review_id"] = container.get("data-review-id", "")

                # Reviewer name
                name_elem = container.select_one(".info_text .member_info .name, .user-name, .name")
                if name_elem:
                    review["reviewer_name"] = name_elem.text.strip()

                # Review date
                date_elem = container.select_one(".rating .date, .review-date, .date, time")
                if date_elem:
                    review["review_date"] = date_elem.get("datetime", date_elem.text.strip())

                # Review title
                title_elem = container.select_one(".title, .review-title, .quote")
                if title_elem:
                    review["title"] = title_elem.text.strip()

                # Review text
                text_elem = container.select_one(".review-body, .entry, .full-text, .reviewText")
                if text_elem:
                    review["review_text"] = text_elem.text.strip()

                # Rating
                rating_elem = container.select_one(".ui_bubble_rating")
                if rating_elem:
                    rating_class = rating_elem.get("class", [])
                    for cls in rating_class:
                        match = re.search(r"bubble_(\d+)", cls)
                        if match:
                            review["rating"] = int(match.group(1)) / 10
                            break

                if review["review_text"]:
                    reviews.append(review)

            except Exception as e:
                print(f"Error parsing review: {e}")
                continue

        return reviews

    def scrape_all(self, max_restaurants: int = 200, max_reviews_per_restaurant: int = 20) -> pd.DataFrame:
        """Main orchestrator - scrape restaurants and reviews."""
        all_data = []

        print("Fetching restaurant list...")
        offset = 0
        restaurants = []

        while len(restaurants) < max_restaurants:
            print(f"Fetching restaurants at offset {offset}...")
            page_restaurants = self.get_restaurant_list(offset=offset)
            if not page_restaurants:
                break
            restaurants.extend(page_restaurants)
            print(f"Got {len(page_restaurants)} restaurants, total: {len(restaurants)}")
            offset += 30

            # Check if we've covered all restaurants (TripAdvisor shows ~30 per page)
            if len(page_restaurants) < 30:
                break

        print(f"Total restaurants found: {len(restaurants)}")

        for i, restaurant in enumerate(restaurants[:max_restaurants]):
            if not restaurant.get("restaurant_id"):
                continue

            print(f"Scraping restaurant {i+1}/{min(len(restaurants), max_restaurants)}: {restaurant['name']}")

            # Get details
            details = self.get_restaurant_details(restaurant["restaurant_id"])
            restaurant.update(details)

            # Get reviews
            reviews = []
            for offset in range(0, max_reviews_per_restaurant, 10):
                page_reviews = self.get_restaurant_reviews(restaurant["restaurant_id"], offset=offset)
                if not page_reviews:
                    break
                reviews.extend(page_reviews)

            # Combine restaurant info with each review
            if reviews:
                for review in reviews:
                    all_data.append({
                        "restaurant_id": restaurant.get("restaurant_id"),
                        "restaurant_name": restaurant.get("name"),
                        "category": restaurant.get("category"),
                        "location": restaurant.get("location"),
                        "price_range": restaurant.get("price_range"),
                        "overall_rating": restaurant.get("overall_rating"),
                        "reviews_count": restaurant.get("reviews_count"),
                        "review_text": review.get("review_text"),
                        "review_date": review.get("review_date"),
                        "reviewer_name": review.get("reviewer_name"),
                        "source": "tripadvisor"
                    })
            else:
                # No reviews, add restaurant with null review
                all_data.append({
                    "restaurant_id": restaurant.get("restaurant_id"),
                    "restaurant_name": restaurant.get("name"),
                    "category": restaurant.get("category"),
                    "location": restaurant.get("location"),
                    "price_range": restaurant.get("price_range"),
                    "overall_rating": restaurant.get("overall_rating"),
                    "reviews_count": restaurant.get("reviews_count"),
                    "review_text": None,
                    "review_date": None,
                    "reviewer_name": None,
                    "source": "tripadvisor"
                })

        return pd.DataFrame(all_data)

    def save_to_csv(self, df: pd.DataFrame, path: str = "data/raw/tripadvisor_reviews.csv"):
        """Save scraped data to CSV."""
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(path, index=False)
        print(f"Saved {len(df)} records to {path}")


def main():
    scraper = TripadvisorScraper(delay_seconds=5.0)
    df = scraper.scrape_all(max_restaurants=100, max_reviews_per_restaurant=20)
    scraper.save_to_csv(df)


if __name__ == "__main__":
    main()
