import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import yfinance as yf

st.set_page_config(page_title="V8 조기경보 백테스트", page_icon="🚀", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700&display=swap');
html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; }
.block-container { padding-top: 3.5rem !important; }
.sig-yellow { color: #d97706; font-weight: 800; }
.sig-red { color: #dc2626; font-weight: 800; }
</style>
""", unsafe_allow_html=True)

st.title("🚀 V8 세이프가드: 조기 경보 시스템(EWS)")
st.caption("타이탄 알파 설계: VIX 모멘텀 필터와 MA50 가속기를 탑재하여 위기 감지 속도를 극대화했습니다.")

# ── 데이터 로딩 (VIX 5일 이동평균 및 MA50 추가) ──
@st.cache_data(ttl=3600, show_spinner=False)
def load_v8_data(ticker, start_year):
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
    
    # V8 핵심 데이터 계산
    combined['VIX_MA5'] = combined['VIX'].rolling(5).mean()
    combined['MA50'] = combined['Close'].rolling(50).mean()
    combined['MA200'] = combined['Close'].rolling(200).mean()
    
    combined['OVX'] = combined['OVX'].fillna(30)
    combined['Spread'] = combined['Spread'].fillna(1.0)
    combined.index = pd.to_datetime(combined.index).tz_localize(None)
    return combined.dropna(subset=['Close', 'VIX', 'MA200'])

# ── [V8 핵심] 조기 경보 판정 로직 ──
def calculate_v8_signals(df):
    df = df.copy()
    W_vix, W_ovx = 1.0, 1.2

    def get_status(row):
        v, o, s, c, m50, m200 = row['VIX'], row['OVX'], row['Spread'], row['Close'], row['MA50'], row['MA200']
        vix_ma5 = row['VIX_MA5']
        
        # 1. MA50 페널티 가중치 (위기 시 감도 2배)
        mult = 2.0 if c < m50 else 1.0
        
        # 2. CMS 계산 (임계치 조정: VIX 25, OVX 35)
        pen = ((W_vix * max(0, v - 25)) + (W_ovx * max(0, o - 35)) + (20 if s < -0.5 else 0)) * mult
        cms = 100 - pen
        
        # 3. VIX Spike (공포의 속도) 감지
        vix_spike = v / vix_ma5 > 1.25 if vix_ma5 > 0 else False
        
        # [V8 단계별 탈출 로직]
        # Stage 2: 생존 우선 (전략적 철수)
        if c < m200 and cms < 50:
            return '🔴도망챠(Red)', cms
            
        # Stage 1: 소나기 피하기 (전술적 후퇴)
        if c < m50 or vix_spike:
            return '🟡조기경보(Yellow)', cms
            
        # 정상 상태
        if cms >= 50:
            return '🟢매수(Green)', cms
        else:
            # 바닥 낚시 (V7 로직 유지)
            if c < (m200 * 0.90): return '🔥역발상매수', cms
            return '🟡관망(Yellow)', cms

    res = df.apply(get_status, axis=1, result_type='expand')
    df['신호'], df['CMS'] = res[0], res[1]
    return df

# ── [V8 핵심] 단계별 비중 조절 ──
def calc_returns_v8(df, start_year):
    df = df.copy()
    start_dt = f"{start_year}-01-01"
    df = df[df.index >= start_dt]
    df['daily_ret'] = df['Close'].pct_change().fillna(0)

    def get_v8_exposure(sig):
        if sig == '🟢매수(Green)': return 1.0
        if sig == '🟡조기경보(Yellow)': return 0.4 # 아우님 설계 반영 (40%)
        if sig == '🟡관망(Yellow)': return 0.7
        if sig == '🔥역발상매수': return 0.8
        return 0.0 # Red는 전량 현금

    # 트레일링 스탑 결합 (V7 세이프가드 유지)
    df['base_exp'] = df['신호'].apply(get_v8_exposure).shift(1).fillna(0)
    final_exp, cur_cum, max_cum = [], 1.0, 1.0
    
    for i in range(len(df)):
        exp, d_ret = df['base_exp'].iloc[i], df['daily_ret'].iloc[i]
        cur_cum *= (1 + d_ret * exp)
        if cur_cum > max_cum: max_cum = cur_cum
        dd = (cur_cum / max_cum) - 1
        # 세이프가드: 고점대비 -8% 시 비중 30%로 강제 축소
        actual_exp = exp * 0.3 if dd < -0.08 else exp
        final_exp.append(actual_exp)

    df['invested'] = final_exp
    df['strat_ret'] = df['daily_ret'] * df['invested']
    df['cum_strat'] = (1 + df['strat_ret']).cumprod()
    df['cum_bah'] = (1 + df['daily_ret']).cumprod()
    return df

# ── UI 및 실행 ──
ticker = st.selectbox("분석 종목", ["QQQ", "SPY", "SOXX"])
start_year = st.selectbox("시작 연도", [2000, 2010, 2020])

with st.spinner("📡 V8 조기경보 레이더 가동 중..."):
    raw = load_v8_data(ticker, start_year)
    sig_df = calculate_v8_signals(raw)
    perf_df = calc_returns_v8(sig_df, start_year)

# 지표 요약
f_strat, f_bah = (perf_df['cum_strat'].iloc[-1]-1)*100, (perf_df['cum_bah'].iloc[-1]-1)*100
mdd_strat = (perf_df['cum_strat']/perf_df['cum_strat'].cummax()-1).min()*100
mdd_bah = (perf_df['cum_bah']/perf_df['cum_bah'].cummax()-1).min()*100

st.markdown("#### 📊 V8 전략 성과 (EWS 적용)")
m1, m2, m3, m4 = st.columns(4)
m1.metric("전략 수익률", f"{f_strat:.1f}%", delta=f"{f_strat - f_bah:.1f}%p")
m2.metric("바이앤홀드", f"{f_bah:.1f}%")
m3.metric("전략 MDD", f"{mdd_strat:.1f}%", delta=f"방어력 {abs(mdd_bah)-abs(mdd_strat):.1f}%p")
m4.metric("B&H MDD", f"{mdd_bah:.1f}%")

# 차트 
fig = make_subplots(rows=2, cols=1, row_heights=[0.7, 0.3], shared_xaxes=True)
fig.add_trace(go.Scatter(x=perf_df.index, y=perf_df['Close'], name='Price'), row=1, col=1)
fig.add_trace(go.Scatter(x=perf_df.index, y=perf_df['MA50'], name='MA50', line=dict(dash='dot', color='cyan')), row=1, col=1)
fig.add_trace(go.Scatter(x=perf_df.index, y=perf_df['MA200'], name='MA200', line=dict(dash='dash', color='orange')), row=1, col=1)
fig.add_trace(go.Scatter(x=perf_df.index, y=(perf_df['cum_strat']-1)*100, name='전략(V8)'), row=2, col=1)
fig.add_trace(go.Scatter(x=perf_df.index, y=(perf_df['cum_bah']-1)*100, name='B&H', line=dict(dash='dot', color='gray')), row=2, col=1)
st.plotly_chart(fig, use_container_width=True)
