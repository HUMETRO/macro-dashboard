import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import yfinance as yf

st.set_page_config(page_title="V7 세이프가드 백테스트", page_icon="🛡️", layout="wide")

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

st.title("🛡️ V7 세이프가드: 수익 보전형 백테스트")
st.caption("수익률 가속 엔진에 '트레일링 스탑'을 결합하여, 수익은 끝까지 지키고 MDD는 획기적으로 낮췄습니다.")

# ── 데이터 로딩 ──
@st.cache_data(ttl=3600, show_spinner=False)
def load_v7_data(ticker, start_year):
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

# ── [V7 핵심] 신호 판정 로직 ──
def calculate_v7_signals(df):
    df = df.copy()
    df['MA200'] = df['Close'].rolling(200).mean()
    W_vix, W_ovx = 1.0, 1.2 # 가중치 최적화

    def get_status(row):
        v, o, s, c, m = row['VIX'], row['OVX'], row['Spread'], row['Close'], row['MA200']
        if pd.isna(m): return '🔴도망챠(Red)', 0
        
        pen = (W_vix * max(0, v - 28)) + (W_ovx * max(0, o - 40)) + (15 if s < -0.5 else 0)
        cms = 100 - pen
        
        if c > m: # 가격이 200일선 위 (상승 추세)
            if cms >= 50: return '🟢매수(Green)', cms
            else: return '🟡관망(Yellow)', cms 
        else: # 가격이 200일선 아래
            if cms < 50 and c < (m * 0.90): return '🔥역발상매수', cms
            return '🔴도망챠(Red)', cms

    res = df.apply(get_status, axis=1, result_type='expand')
    df['신호'], df['CMS'] = res[0], res[1]
    return df

# ── [V7 핵심] 트레일링 스탑 적용 수익률 계산 ──
def calc_returns_v7(df, start_year):
    df = df.copy()
    start_dt = f"{start_year}-01-01"
    df = df[df.index >= start_dt]
    df['daily_ret'] = df['Close'].pct_change().fillna(0)

    # 기본 비중 설정 (공격형)
    def get_base_exposure(sig):
        if sig == '🟢매수(Green)': return 1.0
        if sig == '🟡관망(Yellow)': return 0.7 
        if sig == '🔥역발상매수': return 0.8
        return 0.0

    df['base_exp'] = df['신호'].apply(get_base_exposure).shift(1).fillna(0)
    
    # 🛡️ 트레일링 스탑 시뮬레이션
    final_exp = []
    current_cum = 1.0
    max_cum = 1.0
    
    for i in range(len(df)):
        exp = df['base_exp'].iloc[i]
        d_ret = df['daily_ret'].iloc[i]
        
        # 수익률 업데이트
        current_cum *= (1 + d_ret * exp)
        if current_cum > max_cum: max_cum = current_cum
        
        # 고점 대비 낙폭이 -8% 넘으면 비중 30%로 강제 축소 (세이프가드)
        dd = (current_cum / max_cum) - 1
        actual_exp = exp * 0.3 if dd < -0.08 else exp
        final_exp.append(actual_exp)

    df['invested'] = final_exp
    df['strat_ret'] = df['daily_ret'] * df['invested']
    df['cum_strat'] = (1 + df['strat_ret']).cumprod()
    df['cum_bah'] = (1 + df['daily_ret']).cumprod()
    return df

# ── UI 렌더링 ──
ticker = st.selectbox("분석 종목", ["QQQ", "SPY", "SOXX"])
start_year = st.selectbox("시작 연도", [2000, 2010, 2020])

with st.spinner("📡 V7 세이프가드 엔진 가동 중..."):
    raw = load_v7_data(ticker, start_year)
    sig_df = calculate_v7_signals(raw)
    perf_df = calc_returns_v7(sig_df, start_year)

# 지표 요약
f_strat = (perf_df['cum_strat'].iloc[-1]-1)*100
f_bah = (perf_df['cum_bah'].iloc[-1]-1)*100
mdd_strat = (perf_df['cum_strat']/perf_df['cum_strat'].cummax()-1).min()*100
mdd_bah = (perf_df['cum_bah']/perf_df['cum_bah'].cummax()-1).min()*100

st.markdown("#### 📊 V7 세이프가드 성과 리포트")
m1, m2, m3, m4 = st.columns(4)
m1.metric("전략 수익률", f"{f_strat:.1f}%", delta=f"{f_strat - f_bah:.1f}%p")
m2.metric("바이앤홀드", f"{f_bah:.1f}%")
m3.metric("전략 MDD", f"{mdd_strat:.1f}%", delta=f"방어력 {abs(mdd_bah)-abs(mdd_strat):.1f}%p")
m4.metric("B&H MDD", f"{mdd_bah:.1f}%")

st.markdown("---")
# 차트 
fig = make_subplots(rows=2, cols=1, row_heights=[0.7, 0.3], shared_xaxes=True)
fig.add_trace(go.Scatter(x=perf_df.index, y=perf_df['Close'], name='Price'), row=1, col=1)
fig.add_trace(go.Scatter(x=perf_df.index, y=perf_df['MA200'], name='200일선', line=dict(dash='dash', color='orange')), row=1, col=1)
fig.add_trace(go.Scatter(x=perf_df.index, y=(perf_df['cum_strat']-1)*100, name='전략(V7)'), row=2, col=1)
fig.add_trace(go.Scatter(x=perf_df.index, y=(perf_df['cum_bah']-1)*100, name='B&H', line=dict(dash='dot', color='gray')), row=2, col=1)
st.plotly_chart(fig, use_container_width=True)
