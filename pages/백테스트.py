import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import yfinance as yf

st.set_page_config(page_title="V8-Turbo 레버리지 엔진", page_icon="🏎️", layout="wide")

# ── 스타일 및 헤더 ──
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700&display=swap');
html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; }
.v8-turbo-header { background: linear-gradient(90deg, #1e3a8a, #3b82f6); padding: 20px; border-radius: 10px; color: white; margin-bottom: 25px; }
.sig-box { padding: 10px; border-radius: 5px; text-align: center; font-weight: bold; }
</style>
<div class="v8-turbo-header">
    <h1>🏎️ V8-Turbo: 레버리지 초정밀 방어 시스템</h1>
    <p>TQQQ, QLD, SOXL 전용 | 20일선 조기 반응형 레이더 탑재</p>
</div>
""", unsafe_allow_html=True)

# ── 데이터 로딩 (MA20 추가) ──
@st.cache_data(ttl=3600)
def load_v8_turbo_data(ticker, start_year):
    fetch_start = f"{start_year - 1}-01-01"
    df = yf.download(ticker, start=fetch_start, interval='1d', progress=False)
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    df = df[['Close']].rename(columns={'Close': 'Close'})
    
    # 보조 지표 (VIX, OVX, Spread)
    vix = yf.download("^VIX", start=fetch_start, progress=False)
    ovx = yf.download("^OVX", start=fetch_start, progress=False)
    tnx = yf.download("^TNX", start=fetch_start, progress=False)
    irx = yf.download("^IRX", start=fetch_start, progress=False)
    for d in [vix, ovx, tnx, irx]:
        if isinstance(d.columns, pd.MultiIndex): d.columns = d.columns.get_level_values(0)
        
    combined = df.join(vix['Close'].to_frame('VIX'), how='inner')
    combined = combined.join(ovx['Close'].to_frame('OVX'), how='left')
    combined['Spread'] = (tnx['Close'] - irx['Close'])
    
    # [V8-Turbo 핵심] 이평선 3룡 (20, 50, 200)
    combined['MA20'] = combined['Close'].rolling(20).mean()
    combined['MA50'] = combined['Close'].rolling(50).mean()
    combined['MA200'] = combined['Close'].rolling(200).mean()
    combined['VIX_MA5'] = combined['VIX'].rolling(5).mean()
    
    return combined.fillna(method='ffill').dropna()

# ── V8-Turbo 초정밀 판정 로직 ──
def get_v8_turbo_signals(df):
    df = df.copy()
    def judge(row):
        c, m20, m50, m200 = row['Close'], row['MA20'], row['MA50'], row['MA200']
        v, v_ma5, o, s = row['VIX'], row['VIX_MA5'], row['OVX'], row['Spread']
        
        # 1. 페널티 계산 (레버리지용 민감도 상향)
        mult = 2.5 if c < m50 else 1.0 # 50일선 하회 시 페널티 2.5배
        pen = ((1.0 * max(0, v - 24)) + (1.2 * max(0, o - 34)) + (25 if s < -0.5 else 0)) * mult
        cms = 100 - pen
        
        # 2. VIX Spike (공포의 속도)
        v_spike = v / v_ma5 > 1.25 if v_ma5 > 0 else False
        
        # [V8-Turbo 단계별 대응]
        # Stage 3: 전량 매도 (생존 최우선)
        if c < m200 and cms < 45: return '🔴무조건탈출(Red)', cms
        
        # Stage 2: 초정밀 경보 (20일선 이탈 혹은 VIX 폭발)
        if c < m20 urge or v_spike: return '⚠️초정밀경보(Turbo)', cms
        
        # Stage 1: 정상 및 역발상
        if cms >= 55: return '🟢야수본능(Green)', cms
        if c < (m200 * 0.85): return '🔥역발상매수', cms
        return '🟡안전관망(Yellow)', cms

    res = df.apply(judge, axis=1, result_type='expand')
    df['신호'], df['CMS'] = res[0], res[1]
    return df

# ── 수익률 계산 (레버리지 맞춤 비중) ──
def calc_turbo_performance(df, start_year):
    df = df[df.index >= f"{start_year}-01-01"].copy()
    df['daily_ret'] = df['Close'].pct_change().fillna(0)
    
    def get_exp(sig):
        if sig == '🟢야수본능(Green)': return 1.0
        if sig == '⚠️초정밀경보(Turbo)': return 0.2 # 레버리지는 20%만 남기고 다 팖
        if sig == '🟡안전관망(Yellow)': return 0.5
        if sig == '🔥역발상매수': return 0.8
        return 0.0 # Red는 자비 없이 0%
    
    df['invested'] = df['신호'].apply(get_exp).shift(1).fillna(0)
    df['strat_ret'] = df['daily_ret'] * df['invested']
    df['cum_strat'] = (1 + df['strat_ret']).cumprod()
    df['cum_bah'] = (1 + df['daily_ret']).cumprod()
    return df

# ── 화면 구성 ──
target = st.sidebar.selectbox("레버리지 종목", ["TQQQ", "QLD", "SOXL", "UPRO"])
s_year = st.sidebar.selectbox("시작 연도", [2010, 2015, 2020, 2022])

data = load_v8_turbo_data(target, s_year)
sig_data = get_v8_turbo_signals(data)
perf = calc_turbo_performance(sig_data, s_year)

# 결과 요약
st.subheader(f"📊 {target} 전략 성과 보고")
c1, c2, c3 = st.columns(3)
c1.metric("전략 수익률", f"{(perf['cum_strat'].iloc[-1]-1)*100:.1f}%")
c2.metric("B&H 수익률", f"{(perf['cum_bah'].iloc[-1]-1)*100:.1f}%")
mdd = (perf['cum_strat']/perf['cum_strat'].cummax()-1).min()*100
c3.metric("전략 MDD", f"{mdd:.1f}%", delta="방패 작동 중")

# 차트
fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3])
fig.add_trace(go.Scatter(x=perf.index, y=perf['Close'], name=f"{target} Price"), row=1, col=1)
fig.add_trace(go.Scatter(x=perf.index, y=perf['MA20'], name="MA20(초정밀)", line=dict(color='magenta', dash='dot')), row=1, col=1)
fig.add_trace(go.Scatter(x=perf.index, y=(perf['cum_strat']-1)*100, name="V8-Turbo 전략"), row=2, col=1)
fig.add_trace(go.Scatter(x=perf.index, y=(perf['cum_bah']-1)*100, name="무지성 존버", line=dict(color='gray', dash='dash')), row=2, col=1)
st.plotly_chart(fig, use_container_width=True)
