"""
Streamlit Dashboard Configuration - Enhanced UX/UI
"""

THEME = {
    "primaryColor": "#FF6B6B",
    "backgroundColor": "#0E1117",
    "secondaryBackgroundColor": "#1E2530",
    "textColor": "#FAFAFA",
    "font": "sans-serif"
}

SENTIMENT_COLORS = {
    "positive": "#28a745",
    "neutral": "#ffc107",
    "negative": "#dc3545"
}

RATING_COLORS = {
    "high": "#28a745",      # 4.5+
    "medium": "#ffc107",     # 3.5-4.4
    "low": "#dc3545"         # <3.5
}

CLUSTER_COLORS = [
    "#FF6B6B",  # Red
    "#4ECDC4",  # Teal
    "#45B7D1",  # Blue
    "#96CEB4",  # Green
    "#FFEAA7",  # Yellow
    "#DDA0DD",  # Plum
    "#98D8C8",  # Mint
    "#F7DC6F",  # Gold
]

CUSTOM_CSS = """
<style>
    /* Main background */
    .stApp {
        background-color: #0E1117;
        color: #FAFAFA;
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #1E2530;
        border-right: 1px solid #2D3748;
    }

    /* Headers */
    h1, h2, h3, h4, h5, h6 {
        color: #FAFAFA !important;
    }

    /* Cards */
    [data-testid="stMetricValue"],
    [data-testid="stMetricLabel"] {
        color: #FAFAFA !important;
    }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        background-color: #1E2530;
        border-radius: 8px;
        padding: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        color: #A0AEC0;
    }
    .stTabs [aria-selected="true"] {
        background-color: #FF6B6B;
        color: white !important;
        border-radius: 6px;
    }

    /* Buttons */
    .stButton > button {
        background-color: #FF6B6B;
        color: white;
        border: none;
        border-radius: 6px;
        padding: 0.5rem 1rem;
        font-weight: 600;
    }
    .stButton > button:hover {
        background-color: #FF5252;
    }

    /* Select boxes */
    [data-testid="stSelectbox"] [data-baseweb="select"] {
        background-color: #1E2530;
        border-radius: 6px;
    }

    /* Dataframes */
    .dataframe {
        background-color: #1E2530 !important;
        color: #FAFAFA !important;
    }
    .dataframe th {
        background-color: #2D3748 !important;
    }
    .dataframe td {
        border-color: #2D3748 !important;
    }

    /* Expander */
    .streamlit-expanderHeader {
        background-color: #1E2530;
        border-radius: 6px;
    }

    /* Charts container */
    [data-testid="stHorizontalBlock"] {
        background-color: #1E2530;
        border-radius: 12px;
        padding: 16px;
        margin: 8px 0;
    }

    /* KPI Cards */
    div[data-testid="stMetric"] {
        background-color: #1E2530;
        border-radius: 12px;
        padding: 16px;
        border: 1px solid #2D3748;
    }

    /* Success/Info/Warning boxes */
    .success-box, .info-box, .warning-box {
        border-radius: 8px;
        padding: 16px;
        margin: 8px 0;
    }
    .success-box {
        background-color: rgba(40, 167, 69, 0.15);
        border-left: 4px solid #28a745;
    }
    .warning-box {
        background-color: rgba(255, 193, 7, 0.15);
        border-left: 4px solid #ffc107;
    }

    /* Custom scrollbar */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    ::-webkit-scrollbar-track {
        background: #1E2530;
    }
    ::-webkit-scrollbar-thumb {
        background: #4A5568;
        border-radius: 4px;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: #718096;
    }

    /* Hide default streamlit footer */
    footer {
        visibility: hidden;
    }

</style>
"""
