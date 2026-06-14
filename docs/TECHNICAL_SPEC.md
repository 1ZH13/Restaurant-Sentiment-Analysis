# Technical Specification Document

## 1. System Overview

**Project:** Restaurant Sentiment Analysis Platform
**Location:** Panama City, Panama
**Purpose:** Analyze restaurant reviews from multiple sources to provide insights, sentiment analysis, and recommendations

## 2. Data Sources

### 2.1 Degusta Panama
- **URL:** https://www.degustapanama.com/
- **Data Type:** Restaurant listings with reviews
- **Fields:** Name, category, rating, reviews, location, price range
- **Special:** Aspect ratings (Comida, Servicio, Ambiente)

### 2.2 Tripadvisor Panama
- **URL:** https://www.tripadvisor.com/Restaurants-g294480-Panama_City_Panama_Province.html
- **Data Type:** Restaurant listings with reviews
- **Fields:** Name, rating, reviews count, category, price range
- **Coverage:** 1,470+ restaurants

## 3. Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      DATA SOURCES                               │
│  ┌─────────────────────┐     ┌─────────────────────────────┐   │
│  │   Degusta Panama    │     │    Tripadvisor Panama       │   │
│  │   (Web Scraping)    │     │    (Web Scraping)           │   │
│  └──────────┬──────────┘     └──────────────┬──────────────┘   │
└─────────────┼───────────────────────────────┼───────────────────┘
              │                               │
              ▼                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                      PIPELINE ETL                               │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Extract → Transform → Load                             │   │
│  │  - BeautifulSoup/Requests                              │   │
│  │  - Pandas/Numpy                                        │   │
│  │  - Data cleaning & normalization                       │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      ML/AI LAYER                                │
│  ┌────────────────┐ ┌────────────────┐ ┌────────────────────┐ │
│  │  Sentiment     │ │  Clustering    │ │  Recommendation    │ │
│  │  Analysis      │ │  (K-Means)     │ │  System            │ │
│  │  (LLM + VADER) │ │                │ │                    │ │
│  └────────────────┘ └────────────────┘ └────────────────────┘ │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      DASHBOARD (Streamlit)                      │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐ │
│  │ Overview │ │ Compare  │ │Sentiment │ │ Clustering│ │Recom. │ │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## 4. Modules

### 4.1 Ingestion Module (`src/ingestion/`)
- `degusta_scraper.py` - Scrapes Degusta Panama
- `tripadvisor_scraper.py` - Scrapes Tripadvisor Panama

### 4.2 Preprocessing Module (`src/preprocessing/`)
- `cleaner.py` - Data cleaning operations
- `normalizer.py` - Text normalization
- `feature_engineering.py` - Feature creation

### 4.3 Sentiment Module (`src/sentiment/`)
- `llm_classifier.py` - LLM-based aspect sentiment analysis
- `fallback_classifier.py` - VADER/TextBlob fallback

### 4.4 Clustering Module (`src/clustering/`)
- `restaurant_clusterer.py` - K-Means clustering

### 4.5 Recommendation Module (`src/recommendation/`)
- `recommender.py` - Content-based recommendation system

## 5. Data Schema

### Reviews DataFrame
| Column | Type | Description |
|--------|------|-------------|
| restaurant_id | string | Unique identifier |
| restaurant_name | string | Restaurant name |
| category | string | Cuisine type |
| location | string | Address |
| price_range | string | Price level |
| overall_rating | float | Average rating (1-5) |
| review_text | string | Review content |
| review_date | date | Review date |
| reviewer_name | string | Reviewer name |
| source | string | "degusta" or "tripadvisor" |
| cluster | int | Cluster assignment |
| sentiment_comida_score | float | Food sentiment (-1 to 1) |
| sentiment_servicio_score | float | Service sentiment (-1 to 1) |
| sentiment_precio_score | float | Price sentiment (-1 to 1) |
| sentiment_ambiente_score | float | Atmosphere sentiment (-1 to 1) |

## 6. ML Models

### 6.1 Sentiment Analysis
- **Primary:** OpenAI GPT-3.5 (aspect-based sentiment)
- **Fallback:** VADER Sentiment + TextBlob
- **Aspects:** Comida, Servicio, Precio, Ambiente

### 6.2 Clustering
- **Algorithm:** K-Means
- **Features:** Rating, sentiment scores, price, category
- **Evaluation:** Silhouette Score

## 7. API Endpoints

### 7.1 Web Scraping
- `scrape_restaurant_list()` - Get restaurant listings
- `scrape_restaurant_details()` - Get restaurant details
- `scrape_reviews()` - Get reviews for a restaurant

### 7.2 Sentiment Analysis
- `analyze_review(text)` - Analyze single review
- `analyze_batch(texts)` - Analyze multiple reviews

### 7.3 Recommendation
- `recommend(preferences)` - Get recommendations

## 8. Configuration

### 8.1 Environment Variables
- `OPENAI_API_KEY` - OpenAI API key
- `OLLAMA_BASE_URL` - Ollama server URL
- `REQUEST_DELAY_SECONDS` - Delay between requests

### 8.2 Rate Limiting
- Degusta: 2-3 seconds delay
- Tripadvisor: 5+ seconds delay

## 9. File Structure

```
restaurant-sentiment-analysis/
├── data/
│   ├── raw/          # Raw scraped data
│   ├── processed/    # Cleaned data
│   └── cache/        # API caches
├── src/
│   ├── ingestion/    # Web scrapers
│   ├── preprocessing/  # Data processing
│   ├── sentiment/    # Sentiment analysis
│   ├── clustering/   # ML clustering
│   └── recommendation/  # Recommender
├── dashboard/        # Streamlit app
├── notebooks/        # Jupyter notebooks
├── docs/            # Documentation
└── tests/           # Unit tests
```

## 10. Dependencies

- Python 3.10+
- pandas >= 2.0.0
- numpy >= 1.24.0
- scikit-learn >= 1.3.0
- streamlit >= 1.28.0
- plotly >= 5.18.0
- beautifulsoup4 >= 4.12.0
- requests >= 2.31.0
- openai >= 1.3.0
- vaderSentiment >= 3.3.0
- textblob >= 0.17.0
