import pandas as pd
import ast

# Load synthetic data which has aspect sentiments
df = pd.read_csv('data/raw/synthetic_reviews.csv')
print("Loaded synthetic reviews with aspect sentiments")

# Parse the aspect_sentiments column
def parse_sentiments(s):
    if pd.isna(s):
        return {'comida': 'neutral', 'servicio': 'neutral', 'precio': 'neutral', 'ambiente': 'neutral'}
    try:
        return ast.literal_eval(s)
    except:
        return {'comida': 'neutral', 'servicio': 'neutral', 'precio': 'neutral', 'ambiente': 'neutral'}

df['parsed_sentiments'] = df['aspect_sentiments'].apply(parse_sentiments)

# Extract individual sentiment columns
df['sentiment_comida'] = df['parsed_sentiments'].apply(lambda x: x.get('comida', 'neutral'))
df['sentiment_servicio'] = df['parsed_sentiments'].apply(lambda x: x.get('servicio', 'neutral'))
df['sentiment_precio'] = df['parsed_sentiments'].apply(lambda x: x.get('precio', 'neutral'))
df['sentiment_ambiente'] = df['parsed_sentiments'].apply(lambda x: x.get('ambiente', 'neutral'))

# Convert to numeric scores
sentiment_map = {'positive': 1.0, 'neutral': 0.0, 'negative': -1.0}
df['sentiment_comida_score'] = df['sentiment_comida'].map(sentiment_map)
df['sentiment_servicio_score'] = df['sentiment_servicio'].map(sentiment_map)
df['sentiment_precio_score'] = df['sentiment_precio'].map(sentiment_map)
df['sentiment_ambiente_score'] = df['sentiment_ambiente'].map(sentiment_map)

# Save
output_path = 'data/processed/reviews_with_sentiment.csv'
df.to_csv(output_path, index=False)
print(f"Saved to {output_path}")

# Print distribution
print("\nSentiment distribution:")
for col in ['sentiment_comida', 'sentiment_servicio', 'sentiment_precio', 'sentiment_ambiente']:
    print(f"\n{col}:")
    print(df[col].value_counts())
