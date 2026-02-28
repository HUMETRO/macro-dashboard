import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import yfinance as yf

st.set_page_config(page_title="CMS 신호 백테스트", page_icon="🚦", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700&display=swap');
html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; }
.block-container { padding-top: 3.5rem !important; }
.sig-green { color: #059669; font-weight: 800; }
.sig-yellow { color: #d97706; font-weight: 800; }
.sig-red { color: #dc2626; font-weight: 800; }
.sig-titan { color: #7c3aed; font-weight: 800; }
</style>
""", unsafe_allow_html=True)

st.title("🚦 CMS 통합 신호등 백테스트 (복구본)")
st.caption("VIX, OVX, 금리차를 통합하여 '도망챠'와 '역발상 타점'을 동시에 잡아내는 엔진입니다.")

# ── 데이터 로딩 (VIX, OVX, Spread 포함) ──
@st.cache_data(ttl=3600)
def load_full_macro_data(ticker, start_year):
    fetch_start = f"{start_year - 1}-01-01"
    df = yf.download(ticker, start=fetch_start, interval='1d', progress=False)
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    df = df[['Close']].rename(columns={'Close': 'Close'})
    
    vix = yf.download("^VIX", start=fetch_start, progress=False)
    ovx = yf.download("^OVX", start=fetch_start, progress=False)
    tnx = yf.download("^TNX", start=fetch_start, progress=False)
    irx = yf.download("^IRX", start=fetch_start, progress=False)
    
    for d in [vix, ovx, tnx, irx]:
        if isinstance(d.columns, pd.MultiIndex): d.columns = d.columns.get_level_values(0)
        
    spread = (tnx['Close'] - irx['Close']).to_frame('Spread')
    combined = df.join(vix['Close'].to_frame('VIX'), how='inner')
    combined = combined.join(ovx['Close'].to_frame('OVX'), how='left').join(spread, how='left')
    combined['OVX'] = combined['OVX'].fillna(30)
    combined['Spread'] = combined['Spread'].fillna(1.0)
    return combined.dropna(subset=['Close', 'VIX']).tz_localize(None)

def calculate_cms_logic(df):
    df = df.copy()
    df['MA200'] = df['Close'].rolling(200).mean()
    W_vix, W_ovx = 1.5, 2.0
    
    def get_sig(row):
        v, o, s, c, m = row['VIX'], row['OVX'], row['Spread'], row['Close'], row['MA200']
        pen = (W_vix * max(0, v - 22)) + (W_ovx * max(0, o - 35)) + (20 if s < 0 else 0)
        cms = 100 - pen
        if cms < 55 and pd.notna(m) and c < (m * 0.92): return '🔥역발상매수', cms
        if cms >= 85: return '🟢매수(Green)', cms
        if cms >= 55: return '🟡관망(Yellow)', cms
        return '🔴도망챠(Red)', cms

    res = df.apply(get_sig, axis=1, result_type='expand')
    df['신호'], df['CMS'] = res[0], res[1]
    return df

# ── 실행 및 결과 ──
ticker = st.selectbox("종목 선택", ["QQQ", "SPY", "SOXX"])
start_year = st.selectbox("시작 연도", [2000, 2010, 2020])

raw = load_full_macro_data(ticker, start_year)
sig_df = calculate_cms_logic(raw)
perf_df = sig_df[sig_df.index >= f"{start_year}-01-01"].copy()

perf_df['daily_ret'] = perf_df['Close'].pct_change().fillna(0)
perf_df['invested'] = perf_df['신호'].isin(['🟢매수(Green)', '🔥역발상매수']).shift(1).fillna(0).astype(int)
perf_df['strat_ret'] = perf_df['daily_ret'] * perf_df['invested']
perf_df['cum_strat'] = (1 + perf_df['strat_ret']).cumprod()
perf_df['cum_bah'] = (1 + perf_df['daily_ret']).cumprod()

st.metric("최종 전략 수익률", f"{(perf_df['cum_strat'].iloc[-1]-1)*100:.1f}%")
st.metric("전략 MDD", f"{(perf_df['cum_strat']/perf_df['cum_strat'].cummax()-1).min()*100:.1f}%")

# 차트
fig = make_subplots(rows=1, cols=1)
fig.add_trace(go.Scatter(x=perf_df.index, y=perf_df['Close'], name='Price'))
fig.add_trace(go.Scatter(x=perf_df.index, y=perf_df['MA200'], name='MA200', line=dict(dash='dash')))
st.plotly_chart(fig, use_container_width=True)
