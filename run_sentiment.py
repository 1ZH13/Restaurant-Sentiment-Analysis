import pandas as pd
import os
from dotenv import load_dotenv

load_dotenv()

from src.sentiment.gemini_classifier import AspectSentimentClassifier, process_reviews_with_cache

print("Loading reviews...")
df = pd.read_csv('data/processed/normalized_reviews.csv')
print(f"Found {len(df)} reviews")

# Get unique reviews
reviews = df['review_text'].dropna().unique().tolist()
print(f"Unique reviews: {len(reviews)}")

# Initialize classifier
api_key = os.getenv('GOOGLE_API_KEY', 'AIzaSyBAJcqGrJ3AqRi3NUcNQaIWopt_4kFnhIM')
classifier = AspectSentimentClassifier(model_name='gemini-2.5-flash', api_key=api_key)

# Process reviews
print("\nProcessing reviews with Gemini...")
sample_reviews = reviews[:50]

results = process_reviews_with_cache(sample_reviews, classifier, cache_path='data/cache/sentiment_cache.json')

# Add results to dataframe
for i, result in enumerate(results):
    review_text = sample_reviews[i]
    mask = df['review_text'] == review_text
    if mask.any():
        df.loc[mask, 'sentiment_comida'] = result.comida
        df.loc[mask, 'sentiment_servicio'] = result.servicio
        df.loc[mask, 'sentiment_precio'] = result.precio
        df.loc[mask, 'sentiment_ambiente'] = result.ambiente

# Show results
print("\nSample results:")
for i, result in enumerate(results[:5]):
    print(f"  {i+1}. {result.to_dict()}")

# Save
df.to_csv('data/processed/reviews_with_sentiment.csv', index=False)
print(f"\nSaved to data/processed/reviews_with_sentiment.csv")
