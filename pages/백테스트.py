import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime

st.set_page_config(page_title="공격형 CMS 백테스트", page_icon="⚡", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700&display=swap');
html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; }
.block-container { padding-top: 3.5rem !important; }
.event-card { border-radius: 8px; padding: 10px 14px; margin-bottom: 8px; font-size: 0.84rem; line-height: 1.5; border-left: 4px solid; }
.ev-safe { background:#f0fdf4; border-color:#10b981; }
.ev-danger { background:#fef2f2; border-color:#ef4444; }
.sig-green { color: #059669; font-weight: 800; }
.sig-yellow { color: #d97706; font-weight: 800; }
.sig-red { color: #dc2626; font-weight: 800; }
.sig-titan { color: #7c3aed; font-weight: 800; }
</style>
""", unsafe_allow_html=True)

st.title("⚡ 공격형 CMS 통합 신호등 백테스트")
st.caption("타이탄 알파 V4: 비중 조절(Exposure) 도입 및 200일선 추세 필터로 바이앤홀드를 압도하는 전략입니다.")
st.markdown("---")

# ── 데이터 로딩 ──
@st.cache_data(ttl=3600, show_spinner=False)
def load_macro_data(ticker, start_year):
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
    combined.index = pd.to_datetime(combined.index).tz_localize(None)
    return combined.dropna(subset=['Close', 'VIX'])

# ── [핵심] 아우님의 튜닝 로직 반영 ──
def calculate_attack_cms(df):
    df = df.copy()
    df['MA200'] = df['Close'].rolling(200).mean()
    W_vix, W_ovx = 1.5, 2.0
    
    def get_sig(row):
        v, o, s, c, m = row['VIX'], row['OVX'], row['Spread'], row['Close'], row['MA200']
        if pd.isna(m): return '🔴도망챠(Red)', 0
        
        pen = (W_vix * max(0, v - 22)) + (W_ovx * max(0, o - 35)) + (20 if s < 0 else 0)
        cms = 100 - pen
        
        # 1. 아우님의 역발상 기준 완화 (0.92 -> 0.98)
        if cms < 55 and c < (m * 0.98): return '🔥역발상매수', cms
        
        # 2. 아우님의 추세 필터 (매크로가 안 좋아도 가격이 200일선 위면 등급 유지)
        if cms < 55 and c > m: return '🟡관망(Yellow)', cms
        
        if cms >= 85: return '🟢매수(Green)', cms
        if cms >= 55: return '🟡관망(Yellow)', cms
        return '🔴도망챠(Red)', cms

    res = df.apply(get_sig, axis=1, result_type='expand')
    df['신호'], df['CMS'] = res[0], res[1]
    return df

# ── [핵심] 아우님의 비중 조절 로직 ──
def calc_returns_v4(df, start_year):
    df = df.copy()
    start_dt = f"{start_year}-01-01"
    df = df[df.index >= start_dt]
    df['daily_ret'] = df['Close'].pct_change().fillna(0)

    # 아우님의 추천 Exposure (비중)
    def get_exposure(sig):
        if sig == '🟢매수(Green)': return 1.0     # 풀매수
        if sig == '🔥역발상매수': return 1.2    # 레버리지 공격
        if sig == '🟡관망(Yellow)': return 0.5    # 절반 비중 (기회비용 방어)
        return 0.0                                # 레드(도망)

    df['invested'] = df['신호'].apply(get_exposure).shift(1).fillna(0)
    df['strat_ret'] = df['daily_ret'] * df['invested']
    df['cum_strat'] = (1 + df['strat_ret']).cumprod()
    df['cum_bah'] = (1 + df['daily_ret']).cumprod()
    return df

# ── 실행 ──
ticker = st.selectbox("분석 종목", ["QQQ", "SPY", "SOXX"])
start_year = st.selectbox("시작 연도", [2000, 2010, 2020])

raw = load_macro_data(ticker, start_year)
sig_df = calculate_attack_cms(raw)
perf_df = calc_returns_v4(sig_df, start_year)

# 성과 요약
f_strat = (perf_df['cum_strat'].iloc[-1]-1)*100
f_bah = (perf_df['cum_bah'].iloc[-1]-1)*100
m1, m2, m3, m4 = st.columns(4)
m1.metric("신호전략 수익률", f"{f_strat:.1f}%", delta=f"{f_strat - f_bah:.1f}%p")
m2.metric("바이앤홀드 수익률", f"{f_bah:.1f}%")
m3.metric("전략 최대낙폭(MDD)", f"{(perf_df['cum_strat']/perf_df['cum_strat'].cummax()-1).min()*100:.1f}%")
m4.metric("B&H MDD", f"{(perf_df['cum_bah']/perf_df['cum_bah'].cummax()-1).min()*100:.1f}%")

# 차트
fig = make_subplots(rows=2, cols=1, row_heights=[0.7, 0.3], shared_xaxes=True)
fig.add_trace(go.Scatter(x=perf_df.index, y=perf_df['Close'], name='Price'), row=1, col=1)
fig.add_trace(go.Scatter(x=perf_df.index, y=perf_df['MA200'], name='200일선', line=dict(dash='dash')), row=1, col=1)
fig.add_trace(go.Scatter(x=perf_df.index, y=(perf_df['cum_strat']-1)*100, name='전략(V4) 수익률'), row=2, col=1)
fig.add_trace(go.Scatter(x=perf_df.index, y=(perf_df['cum_bah']-1)*100, name='바이앤홀드', line=dict(dash='dot')), row=2, col=1)
st.plotly_chart(fig, use_container_width=True)
