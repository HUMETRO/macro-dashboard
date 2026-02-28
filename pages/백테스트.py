import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import yfinance as yf

st.set_page_config(page_title="MDD 사냥꾼 백테스트", page_icon="🛡️", layout="wide")

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

st.title("🛡️ MDD 사냥꾼: 이중 필터 CMS 백테스트")
st.caption("타이탄 알파 V5: 200일선 추세 필터를 최우선으로 하여 엇박자를 방지하고 대폭락을 원천 차단합니다.")

# ── 데이터 로딩 (VIX, OVX, Spread) ──
@st.cache_data(ttl=3600, show_spinner=False)
def load_dual_filter_data(ticker, start_year):
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

# ── [핵심] 아우님의 이중 필터 로직 ──
def calculate_dual_filter_cms(df):
    df = df.copy()
    df['MA200'] = df['Close'].rolling(200).mean()
    W_vix, W_ovx = 1.5, 2.0  # 가중치 유지

    def get_status(row):
        v, o, s, c, m = row['VIX'], row['OVX'], row['Spread'], row['Close'], row['MA200']
        if pd.isna(m): return '🔴도망챠(Red)', 0
        
        # 1. CMS 계산 (임계치 조정: VIX 25, OVX 40)
        pen = (W_vix * max(0, v - 25)) + (W_ovx * max(0, o - 40)) + (30 if s < 0 else 0)
        cms = 100 - pen
        
        # 2. 판정 로직 개조 (Trend-First)
        if c > m: # 가격이 200일선 위 (상승 추세)
            if cms >= 60: return '🟢매수(Green)', cms
            else: return '🟡관망(Yellow)', cms # 매크로 안 좋아도 추세 위면 홀딩(비중축소)
        else: # 가격이 200일선 아래 (하락 추세)
            # 진짜 폭락했을 때만 역발상 (기준 0.85로 강화)
            if cms < 45 and c < (m * 0.85): return '🔥역발상매수', cms
            return '🔴도망챠(Red)', cms # 200일선 아래면 기본적으로 도망 (MDD 방어)

    res = df.apply(get_status, axis=1, result_type='expand')
    df['신호'], df['CMS'] = res[0], res[1]
    return df

# ── [비중 조절] 아우님의 익스포저 가이드 ──
def calc_returns_v5(df, start_year):
    df = df.copy()
    start_dt = f"{start_year}-01-01"
    df = df[df.index >= start_dt]
    df['daily_ret'] = df['Close'].pct_change().fillna(0)

    def get_exposure(sig):
        if sig == '🟢매수(Green)': return 1.0
        if sig == '🟡관망(Yellow)': return 0.6  # 비중 축소로 방어
        if sig == '🔥역발상매수': return 0.4  # 바닥 낚시는 소량만 (MDD 관리)
        return 0.0                             # Red는 무조건 현금

    df['invested'] = df['신호'].apply(get_exposure).shift(1).fillna(0)
    df['strat_ret'] = df['daily_ret'] * df['invested']
    df['cum_strat'] = (1 + df['strat_ret']).cumprod()
    df['cum_bah'] = (1 + df['daily_ret']).cumprod()
    return df

# ── 결과 출력 ──
ticker = st.selectbox("분석 종목", ["QQQ", "SPY", "SOXX"])
start_year = st.selectbox("시작 연도", [2000, 2010, 2020])

with st.spinner("📡 이중 필터 엔진 구동 중..."):
    raw = load_dual_filter_data(ticker, start_year)
    sig_df = calculate_dual_filter_cms(raw)
    perf_df = calc_returns_v5(sig_df, start_year)

# 지표 계산
f_strat = (perf_df['cum_strat'].iloc[-1]-1)*100
f_bah = (perf_df['cum_bah'].iloc[-1]-1)*100
mdd_strat = (perf_df['cum_strat']/perf_df['cum_strat'].cummax()-1).min()*100
mdd_bah = (perf_df['cum_bah']/perf_df['cum_bah'].cummax()-1).min()*100

st.markdown("#### 📊 V5 이중 필터 전략 성과")
m1, m2, m3, m4 = st.columns(4)
m1.metric("전략 수익률", f"{f_strat:.1f}%", delta=f"{f_strat - f_bah:.1f}%p")
m2.metric("바이앤홀드", f"{f_bah:.1f}%")
m3.metric("전략 MDD", f"{mdd_strat:.1f}%", delta=f"방어력 {abs(mdd_bah)-abs(mdd_strat):.1f}%p", delta_color="normal")
m4.metric("B&H MDD", f"{mdd_bah:.1f}%")

st.markdown("---")
# 차트 
fig = make_subplots(rows=2, cols=1, row_heights=[0.7, 0.3], shared_xaxes=True)
fig.add_trace(go.Scatter(x=perf_df.index, y=perf_df['Close'], name='Price'), row=1, col=1)
fig.add_trace(go.Scatter(x=perf_df.index, y=perf_df['MA200'], name='200일선', line=dict(dash='dash', color='gray')), row=1, col=1)
fig.add_trace(go.Scatter(x=perf_df.index, y=(perf_df['cum_strat']-1)*100, name='전략(V5)'), row=2, col=1)
fig.add_trace(go.Scatter(x=perf_df.index, y=(perf_df['cum_bah']-1)*100, name='B&H', line=dict(dash='dot')), row=2, col=1)
st.plotly_chart(fig, use_container_width=True)
