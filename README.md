# Restaurant Sentiment Analysis Platform

Platform for analyzing restaurant reviews in Panama City using data science, machine learning, and AI techniques.

## Project Structure

```
restaurant-sentiment-analysis/
├── data/               # Data files
│   ├── raw/           # Raw scraped data
│   ├── processed/     # Cleaned and processed data
│   └── cache/        # Cached API responses
├── src/              # Source code
│   ├── ingestion/    # Web scraping
│   ├── preprocessing/  # Data cleaning
│   ├── sentiment/   # Sentiment analysis
│   ├── clustering/  # Restaurant clustering
│   ├── recommendation/  # Recommender system
│   └── load/        # Data loading
├── dashboard/        # Streamlit dashboard
├── notebooks/        # Jupyter notebooks
├── docs/            # Documentation
└── tests/           # Unit tests
```

## Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys
```

## Data Sources

Two **real**, independent sources of Panama City restaurant reviews:

- **Degusta Panamá** — https://www.degustapanama.com/
  Reviews are embedded as schema.org microdata and scraped with
  `requests` + `BeautifulSoup` (`src/ingestion/degusta_scraper.py`).
- **RestaurantGuru** — https://restaurantguru.com/Panama-City
  Aggregates real customer reviews (mostly from Google), scraped with
  `src/ingestion/restaurantguru_scraper.py`.

> **Note on Tripadvisor:** the originally planned second source
> (https://www.tripadvisor.com/Restaurants-g294480-Panama_City_Panama_Province.html)
> returns **HTTP 403 + captcha** to scrapers, so RestaurantGuru is used instead.
> The Tripadvisor scraper is kept in `src/ingestion/tripadvisor_scraper.py` for reference.

## Usage

The processed dataset is committed under `data/`, so you can launch the dashboard
right away:

```bash
streamlit run dashboard/app.py
```

### Regenerating the data (full pipeline)

**Option A — one command** (runs the whole ETL + ML from the scraped source files):

```bash
python run_pipeline.py
```

**Option B — step by step:**

```bash
# 1. Ingest the two real sources (live scraping, rate-limited)
python -m src.ingestion.degusta_scraper           # -> data/raw/degusta_reviews.csv
python -m src.ingestion.restaurantguru_scraper    # -> data/raw/restaurantguru_reviews.csv

# 2. Combine sources + tag aspect sentiment
python -m src.ingestion.build_dataset             # -> data/raw/raw_reviews.csv

# 3. ETL: clean -> normalize -> features
python -m src.preprocessing.cleaner
python -m src.preprocessing.normalizer
python -m src.preprocessing.feature_engineering

# 4. ML: clustering (writes the dashboard's canonical file)
python -m src.clustering.restaurant_clusterer     # -> data/processed/restaurants_clustered.csv

# 5. Dashboard
streamlit run dashboard/app.py
```

## Sentiment Analysis

Aspect-based sentiment (comida / servicio / precio / ambiente) is computed per
review. The default classifier is a **Spanish/English lexicon analyzer** with
negation handling (`src/sentiment/fallback_classifier.py`) — it needs **no API
key** and works well on Spanish reviews. An LLM classifier (Google Gemini,
`src/sentiment/gemini_classifier.py`) can be plugged in by setting `GOOGLE_API_KEY`
in `.env`.

## Team

- Grupo 5: Restaurant Sentiment Analysis Platform

## License

MIT
