import streamlit as st
import plotly.graph_objects as go
import sys
import os
import pandas as pd
import numpy as np
import yfinance as yf

# [1] 경로 설정
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# [2] 부품 로드
try:
    from data_fetcher import get_all_market_data
    from calculations import calculate_sector_scores, calculate_individual_metrics, calculate_core_sector_scores
except ImportError as e:
    st.error(f"🚨 부품 로딩 실패! (에러: {e})")
    st.stop()

st.set_page_config(page_title="매크로 위험알리미", page_icon="📊", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700&display=swap');
html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; }
.block-container { padding-top: 3.5rem !important; }

/* ── 카드 스타일 ── */
.metric-card, .stock-card, .core-card {
    background: #fff; border-radius: 8px; padding: 10px 12px; border: 1px solid #e5e7eb; margin-bottom: 8px; min-width: 0; word-break: break-word;
}
.buy-signal, .stock-up, .core-strong { border-left: 5px solid #10b981; background: #f0fdf4; }
.sell-signal, .stock-down, .core-weak { border-left: 5px solid #ef4444; background: #fef2f2; }
.wait-signal, .core-mid { border-left: 5px solid #f59e0b; background: #fffbeb; }
.stock-flat { border-left: 5px solid #9ca3af; background: #f9fafb; }

.ticker-header, .stock-name, .core-name { font-size: 0.85rem; font-weight: 700; color: #111827; margin-bottom: 3px; }
.score-box, .stock-meta, .core-meta { font-size: 0.75rem; color: #374151; line-height: 1.5; }
.stock-price { font-size: 1.05rem; font-weight: 800; margin-bottom: 2px; }
.core-score { font-size: 1.1rem; font-weight: 800; margin-bottom: 2px; }

@media (max-width: 640px) {
    .block-container { padding-top: 4rem !important; }
    h1 { font-size: 1.2rem !important; }
    .ticker-header, .stock-name, .core-name { font-size: 0.78rem; }
    .score-box, .stock-meta, .core-meta { font-size: 0.68rem; }
}
</style>
""", unsafe_allow_html=True)

st.title("📊 매크로경제 위험알리미")
st.markdown("---")

# 💡 VIX 및 금리차 실시간 수집 엔진
@st.cache_data(ttl=300)
def get_macro_indicators():
    try:
        vix_df = yf.download("^VIX", period="5d", progress=False)['Close']
        tnx_df = yf.download("^TNX", period="5d", progress=False)['Close'] # 10년물
        irx_df = yf.download("^IRX", period="5d", progress=False)['Close'] # 3개월물
        
        vix = vix_df.iloc[-1].item() if isinstance(vix_df, pd.DataFrame) else vix_df.iloc[-1]
        tnx = tnx_df.iloc[-1].item() if isinstance
