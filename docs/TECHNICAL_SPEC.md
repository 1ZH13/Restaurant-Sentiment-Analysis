# Technical Specification Document

## 1. System Overview

**Project:** Restaurant Sentiment Analysis Platform  
**Location:** Panama City, Panama  
**Purpose:** Collect restaurant reviews from multiple real sources, analyze aspect-level sentiment, group similar restaurants with clustering, and show the results in an interactive dashboard with recommendations.

---

## 2. Problem Statement and Business Value

The main problem addressed by this platform is the difficulty of comparing restaurant opinions that are scattered across different online sources. Users often need to decide where to eat, but they do not have a unified view of quality, price, service, or food satisfaction.

This project solves that problem by turning raw textual reviews into structured data and visual insights:
- what people praise most,
- what they criticize,
- which restaurants perform better overall,
- and which ones are better suited to a user’s preferences.

---

## 3. Data Sources and Dataset Usage

### 3.1 Real data sources
The current implementation uses two real sources:

1. Degusta Panamá  
   URL: https://www.degustapanama.com/
2. RestaurantGuru  
   URL: https://restaurantguru.com/Panama-City

### 3.2 What is done with the dataset
The project performs the following operations:
- scrapes restaurant reviews and metadata,
- combines both sources in one unified file,
- removes duplicates and empty records,
- normalizes the text,
- generates sentiment scores by aspect,
- and prepares the dataset for ML and dashboard visualization.

### 3.3 Current dataset size
Verified project data currently contains:
- 973 reviews from Degusta,
- 24 reviews from RestaurantGuru,
- 997 unified reviews across 207 restaurants in the processed dataset.

Field coverage: price range 100%, zone 100%, restaurant rating 100%, cuisine 99%,
per-review rating 98%, review date 98%. Review dates span 2019 to 2026.

### 3.4 Identity and deduplication
Restaurants are identified by a canonical id derived from the normalised
restaurant name, so the same venue listed by both sources collapses into one
entity. Per-source ids are retained in `source_restaurant_id` for traceability.

RestaurantGuru ids are derived from an MD5 of the URL slug. They were previously
built from Python's built-in `hash()`, which is randomised per process, so every
run produced different ids for the same restaurant and nothing could be joined or
deduplicated across runs.

Reviews are deduplicated within a restaurant by comparing normalised text
(lowercased, accents and punctuation removed).

---

## 4. Architecture and Pipeline

The system follows an ETL + ML + Dashboard flow:

```text
Scraping (Degusta + RestaurantGuru)
        ↓
Ingestion and unification
        ↓
Cleaning + normalization + feature engineering
        ↓
Aspect sentiment analysis
        ↓
K-Means clustering
        ↓
Streamlit dashboard + recommendation engine
```

### 4.1 Ingestion
Implemented in:
- src/ingestion/degusta_scraper.py
- src/ingestion/restaurantguru_scraper.py
- src/ingestion/build_dataset.py

This stage collects real reviews, stores them in data/raw/, and builds the unified dataset.

### 4.2 Preprocessing and transformation
Implemented in:
- src/preprocessing/cleaner.py
- src/preprocessing/normalizer.py
- src/preprocessing/feature_engineering.py

This stage:
- removes duplicates,
- cleans special characters and HTML noise,
- normalizes lowercase/accents/spacing,
- removes stopwords and tokenizes text,
- generates useful statistics such as word count and restaurant-level aggregates.

---

## 5. Aspect-Based Sentiment Analysis

### 5.1 What it is
Aspect-based sentiment analysis identifies the polarity of an opinion for specific attributes, not just the review as a whole.

The project evaluates:
- comida
- servicio
- precio
- ambiente

### 5.2 How it works
Each review is analyzed and converted into a score that indicates whether the user opinion about that aspect is positive, neutral, or negative.

### 5.3 Implementation in this project
- Default sentiment analyzer: src/sentiment/fallback_classifier.py
- Optional LLM-based path: src/sentiment/gemini_classifier.py

The default behavior is lexical and does not require a paid API key. The LLM route is available to improve semantic interpretation when an API key is configured.

---

## 6. Clustering of Restaurants

### 6.1 What it is
Clustering groups restaurants with similar characteristics into clusters, without needing pre-labeled categories.

### 6.2 Applied technique
The implemented technique is K-Means.

### 6.3 Why it is used
It helps identify patterns such as:
- premium restaurants,
- budget-friendly options,
- restaurants with strong food reputation,
- locations with better service perception.

### 6.4 Implementation details
The clustering module is in:
- src/clustering/restaurant_clusterer.py

Clustering is performed **at the restaurant level**: the reviews table is first
aggregated to one row per restaurant, and the resulting labels are mapped back
onto the reviews at the end. Aggregating matters — building the matrix with
`groupby(...).transform(...)` yields one row per review with identical values
repeated per restaurant, which both inflates the silhouette score and weights a
restaurant by how many reviews it happens to have.

It uses features such as:
- average rating,
- aspect sentiment averages,
- review count,
- average review length,
- price level (1-4, from the shared price encoder).

The number of clusters is selected with the silhouette score over k = 2..9, and
the model is then trained with that value. The observed silhouette is around
0.17, which is low: restaurants do not separate into sharply defined groups, and
the figure is reported as-is rather than tuned upward.

Each cluster is named after the metric on which it stands out relative to the
other clusters (metrics are standardised across clusters), which guarantees
distinct, informative names. The name is persisted in the `cluster_name` column.

---

## 7. Recommendation System

### 7.1 What it is
The recommendation engine helps the user find restaurants that best match their preferences.

### 7.2 How it works
It scores each restaurant according to:
- cuisine category,
- price range,
- general rating,
- sentiment in priority aspects,
- and other profile features.

### 7.3 Implementation
Implemented in:
- src/recommendation/recommender.py

This system uses content-based filtering, meaning recommendations are based on the characteristics of the restaurant and the preferences expressed by the user.

---

## 8. Interactive Dashboard with Streamlit

### 8.1 What it is
Streamlit is the framework used to create the web dashboard of the project.

### 8.2 Why it is used
It allows fast development of an interactive interface without requiring a large front-end stack.

### 8.3 How it works in this project
The main dashboard entry point is:
- dashboard/app.py

It loads the processed dataset and renders visual sections for:
- overview,
- comparison,
- sentiment,
- clustering,
- recommendations,
- and detailed restaurant views.

This gives the user a practical way to explore the analysis and compare restaurants in real time.

---

## 9. Technical Requirements

The project uses the following main technologies:

- Python 3.10+
- pandas
- numpy
- scikit-learn
- streamlit
- plotly
- beautifulsoup4
- requests
- lxml
- nltk
- textblob
- vaderSentiment
- google-generativeai
- openai
- pytest

These components support the complete workflow: scraping, transformation, analysis, ML, and interactive visualization.

---

## 10. Implementation Summary

In summary, this project implements the following:
1. Real review dataset collection from two sources.
2. Pipeline ETL for ingestion, cleaning, normalization, and feature engineering.
3. Aspect-based sentiment analysis using lexical analysis and optional LLM support.
4. K-Means clustering to discover restaurant profiles.
5. Recommendation logic based on user preferences.
6. Interactive visual dashboard using Streamlit.

This combination makes the platform a complete academic solution for restaurant opinion analysis in Panama.

