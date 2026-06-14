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

- **Degusta Panamá** - https://www.degustapanama.com/
- **Tripadvisor Panama** - https://www.tripadvisor.com/

## Usage

### 1. Scrape Data
```bash
python -m src.ingestion.degusta_scraper
python -m src.ingestion.tripadvisor_scraper
```

### 2. Process Data
```bash
python -m src.preprocessing.cleaner
python -m src.preprocessing.normalizer
```

### 3. Run Analysis
```bash
python -m src.sentiment.llm_classifier
python -m src.clustering.restaurant_clusterer
```

### 4. Start Dashboard
```bash
streamlit run dashboard/app.py
```

## Team

- Grupo 5: Restaurant Sentiment Analysis Platform

## License

MIT
