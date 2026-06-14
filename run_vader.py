import pandas as pd
from src.sentiment.fallback_classifier import VADERSentimentAnalyzer, sentiment_to_numeric

print("Loading reviews...")
df = pd.read_csv('data/processed/normalized_reviews.csv')
print(f"Found {len(df)} reviews")

# Check for existing sentiment data
if 'sentiment_comida' in df.columns:
    existing = df['sentiment_comida'].notna().sum()
    print(f"Existing sentiment data: {existing}")
else:
    print("No existing sentiment data")

# Use VADER for all sentiment analysis
print("\nAnalyzing sentiment with VADER...")
analyzer = VADERSentimentAnalyzer()

# Process all reviews
for idx, row in df.iterrows():
    if idx % 50 == 0:
        print(f"Processing {idx}/{len(df)}...")

    review_text = row.get('review_text', '')
    if pd.isna(review_text) or not review_text:
        continue

    # Get aspect sentiment
    sentiments = analyzer.get_aspect_sentiment(review_text)

    df.at[idx, 'sentiment_comida'] = sentiments['comida']
    df.at[idx, 'sentiment_servicio'] = sentiments['servicio']
    df.at[idx, 'sentiment_precio'] = sentiments['precio']
    df.at[idx, 'sentiment_ambiente'] = sentiments['ambiente']

    # Also add numeric scores
    df.at[idx, 'sentiment_comida_score'] = sentiment_to_numeric(sentiments['comida'])
    df.at[idx, 'sentiment_servicio_score'] = sentiment_to_numeric(sentiments['servicio'])
    df.at[idx, 'sentiment_precio_score'] = sentiment_to_numeric(sentiments['precio'])
    df.at[idx, 'sentiment_ambiente_score'] = sentiment_to_numeric(sentiments['ambiente'])

# Save
output_path = 'data/processed/reviews_with_sentiment.csv'
df.to_csv(output_path, index=False)
print(f"\nSaved to {output_path}")

# Print summary
print("\nSentiment distribution:")
for aspect in ['comida', 'servicio', 'precio', 'ambiente']:
    col = f'sentiment_{aspect}'
    if col in df.columns:
        print(f"\n{aspect.capitalize()}:")
        print(df[col].value_counts())
