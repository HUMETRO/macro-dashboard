import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import yfinance as yf

st.set_page_config(page_title="V7 위기검증 백테스트", page_icon="🛡️", layout="wide")

# ── 스타일 설정 ──
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700&display=swap');
html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; }
.block-container { padding-top: 3.5rem !important; }
.event-card { border-radius: 8px; padding: 12px 16px; margin-bottom: 10px; font-size: 0.9rem; line-height: 1.6; border-left: 5px solid; }
.ev-safe   { background:#f0fdf4; border-color:#10b981; color: #166534; }
.ev-danger { background:#fef2f2; border-color:#ef4444; color: #991b1b; }
.sig-text  { font-weight: 800; font-size: 1.05rem; }
</style>
""", unsafe_allow_html=True)

st.title("🛡️ V7 세이프가드 & 경제위기 회피 검증")
st.caption("수익률은 V7 엔진으로 극대화하고, 과거 경제 위기 시 '도망챠' 신호가 정확히 작동했는지 검증합니다.")

# ── 역사적 위기 리스트 ──
EVENTS = [
    {"date": "2000-03-24", "name": "닷컴버블 붕괴", "type": "danger", "desc": "나스닥 -80% 하락의 시작. 과연 우리 신호는?"},
    {"date": "2008-09-15", "name": "리먼 브라더스 파산", "type": "danger", "desc": "금융위기 정점. 금리차 역전과 VIX 폭발 시기"},
    {"date": "2009-03-09", "name": "금융위기 대바닥", "type": "safe", "desc": "공포가 극에 달했을 때의 역발상 매수 타점"},
    {"date": "2018-10-10", "name": "미중 무역전쟁 폭락", "type": "danger", "desc": "금리 인상과 무역 갈등으로 인한 하락장"},
    {"date": "2020-02-24", "name": "코로나 팬데믹 쇼크", "type": "danger", "desc": "역사상 가장 빠른 속도의 폭락 구간"},
    {"date": "2020-03-23", "name": "코로나 최저점", "type": "safe", "desc": "무제한 양적완화와 V자 반등의 시작점"},
    {"date": "2022-01-05", "name": "인플레이션 하락장", "type": "danger", "desc": "금리 인상 본격화로 인한 1년 내내 하락"}
]

# ── 데이터 로딩 ──
@st.cache_data(ttl=3600, show_spinner=False)
def load_v7_full_data(ticker, start_year):
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

# ── V7 신호 로직 ──
def calculate_v7_logic(df):
    df = df.copy()
    df['MA200'] = df['Close'].rolling(200).mean()
    W_vix, W_ovx = 1.0, 1.2

    def get_status(row):
        v, o, s, c, m = row['VIX'], row['OVX'], row['Spread'], row['Close'], row['MA200']
        if pd.isna(m): return '🔴도망챠(Red)', 0
        pen = (W_vix * max(0, v - 28)) + (W_ovx * max(0, o - 40)) + (15 if s < -0.5 else 0)
        cms = 100 - pen
        if c > m:
            if cms >= 50: return '🟢매수(Green)', cms
            else: return '🟡관망(Yellow)', cms 
        else:
            if cms < 50 and c < (m * 0.90): return '🔥역발상매수', cms
            return '🔴도망챠(Red)', cms

    res = df.apply(get_status, axis=1, result_type='expand')
    df['신호'], df['CMS'] = res[0], res[1]
    return df

# ── V7 수익률 계산 (트레일링 스탑 포함) ──
def calc_returns_v7_final(df, start_year):
    df = df.copy()
    start_dt = f"{start_year}-01-01"
    df = df[df.index >= start_dt]
    df['daily_ret'] = df['Close'].pct_change().fillna(0)

    def get_base_exp(sig):
        if sig == '🟢매수(Green)': return 1.0
        if sig == '🟡관망(Yellow)': return 0.7 
        if sig == '🔥역발상매수': return 0.8
        return 0.0

    df['base_exp'] = df['신호'].apply(get_base_exp).shift(1).fillna(0)
    
    final_exp, cur_cum, max_cum = [], 1.0, 1.0
    for i in range(len(df)):
        exp, d_ret = df['base_exp'].iloc[i], df['daily_ret'].iloc[i]
        cur_cum *= (1 + d_ret * exp)
        if cur_cum > max_cum: max_cum = cur_cum
        dd = (cur_cum / max_cum) - 1
        actual_exp = exp * 0.3 if dd < -0.08 else exp
        final_exp.append(actual_exp)

    df['invested'] = final_exp
    df['strat_ret'] = df['daily_ret'] * df['invested']
    df['cum_strat'] = (1 + df['strat_ret']).cumprod()
    df['cum_bah'] = (1 + df['daily_ret']).cumprod()
    return df

# ── 실행부 ──
col_top1, col_top2 = st.columns([2, 1])
with col_top1: ticker = st.selectbox("분석 종목", ["QQQ", "SPY", "SOXX"])
with col_top2: start_year = st.selectbox("시작 연도", [2000, 2010, 2020])

raw = load_v7_full_data(ticker, start_year)
sig_df = calculate_v7_logic(raw)
perf_df = calc_returns_v7_final(sig_df, start_year)

# ── 성과 요약 ──
f_strat, f_bah = (perf_df['cum_strat'].iloc[-1]-1)*100, (perf_df['cum_bah'].iloc[-1]-1)*100
mdd_strat = (perf_df['cum_strat']/perf_df['cum_strat'].cummax()-1).min()*100
mdd_bah = (perf_df['cum_bah']/perf_df['cum_bah'].cummax()-1).min()*100

st.markdown("#### 📊 V7 전략 성과 요약")
m1, m2, m3, m4 = st.columns(4)
m1.metric("전략 수익률", f"{f_strat:.1f}%", delta=f"{f_strat - f_bah:.1f}%p")
m2.metric("바이앤홀드", f"{f_bah:.1f}%")
m3.metric("전략 MDD", f"{mdd_strat:.1f}%", delta=f"방어력 {abs(mdd_bah)-abs(mdd_strat):.1f}%p")
m4.metric("B&H MDD", f"{mdd_bah:.1f}%")

# ── 차트 ──
fig = make_subplots(rows=2, cols=1, row_heights=[0.7, 0.3], shared_xaxes=True)
fig.add_trace(go.Scatter(x=perf_df.index, y=perf_df['Close'], name='Price'), row=1, col=1)
fig.add_trace(go.Scatter(x=perf_df.index, y=perf_df['MA200'], name='200일선', line=dict(dash='dash', color='orange')), row=1, col=1)
fig.add_trace(go.Scatter(x=perf_df.index, y=(perf_df['cum_strat']-1)*100, name='전략(V7)'), row=2, col=1)
fig.add_trace(go.Scatter(x=perf_df.index, y=(perf_df['cum_bah']-1)*100, name='B&H', line=dict(dash='dot', color='gray')), row=2, col=1)
st.plotly_chart(fig, use_container_width=True)

# ── 역사적 위기 검증표 복구! ──
st.markdown("---")
st.markdown("#### 🎯 역사적 경제위기 회피 검증")
ev_cols = st.columns(2)
for i, ev in enumerate(EVENTS):
    ev_date = pd.Timestamp(ev['date'])
    available = perf_df.index[perf_df.index >= ev_date]
    if len(available) == 0: continue
    row = perf_df.loc[available[0]]
    sig = row['신호']
    
    # 신호에 따른 색상 정의
    sig_color = "red" if "도망챠" in sig else ("orange" if "관망" in sig else "green")
    if "역발상" in sig: sig_color = "purple"
    
    with ev_cols[i % 2]:
        st.markdown(f"""
<div class="event-card {'ev-safe' if ev['type']=='safe' else 'ev-danger'}">
    <b>📅 {ev['date']} | {ev['name']}</b><br>
    <span style="color:{sig_color}; font-weight:800; font-size:1.1rem;">당시 신호: {sig}</span><br>
    <small>CMS 점수: {row['CMS']:.1f}점 | {ev['desc']}</small>
</div>
""", unsafe_allow_html=True)
