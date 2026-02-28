import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime

st.set_page_config(page_title="CMS 신호 백테스트", page_icon="🚦", layout="wide")

# ── 스타일 설정 (신호등 색상 등) ──
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700&display=swap');
html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; }
.block-container { padding-top: 3.5rem !important; }

.event-card { border-radius: 8px; padding: 10px 14px; margin-bottom: 8px; font-size: 0.84rem; line-height: 1.5; border-left: 4px solid; }
.ev-safe   { background:#f0fdf4; border-color:#10b981; }
.ev-danger { background:#fef2f2; border-color:#ef4444; }

.sig-green  { color: #059669; font-weight: 800; }
.sig-yellow { color: #d97706; font-weight: 800; }
.sig-red    { color: #dc2626; font-weight: 800; }
.sig-titan  { color: #7c3aed; font-weight: 800; }
</style>
""", unsafe_allow_html=True)

st.title("🚦 CMS 통합 신호등 백테스트 (최종 복구판)")
st.caption("타이탄 알파 설계도 기반: 현실적인 수익률 계산(shift)과 바이앤홀드 비교 기능이 완벽히 복구되었습니다.")
st.markdown("---")

# ── 역사적 이벤트 리스트 ──
EVENTS = [
    {"date": "2000-03-24", "name": "닷컴버블 붕괴 시작", "type": "danger", "desc": "추세 붕괴 및 VIX 상승 구간"},
    {"date": "2008-09-15", "name": "리먼 파산 (금융위기)", "type": "danger", "desc": "신용 스프레드 폭발 및 🔴빨간불 지속 구간"},
    {"date": "2009-03-09", "name": "금융위기 대바닥", "type": "safe", "desc": "🔥역발상 매수 타점(Purple) 발생 구간"},
    {"date": "2020-02-24", "name": "코로나 팬데믹 폭락", "type": "danger", "desc": "VIX 폭등에 따른 즉각적인 대피 신호"},
    {"date": "2020-03-23", "name": "코로나 최저점", "type": "safe", "desc": "역사적 V자 랠리 및 🔥역발상 매수 신호"},
    {"date": "2022-01-05", "name": "인플레이션 & 긴축", "type": "danger", "desc": "금리차 역전 및 1년 내내 이어진 베어마켓"}
]

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

# ── CMS 시그널 계산 ──
def calculate_cms_signals(df):
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

# ── 수익률 계산 ──
def calc_returns(df, start_year):
    df = df.copy()
    start_dt = f"{start_year}-01-01"
    df = df[df.index >= start_dt]
    df['daily_ret'] = df['Close'].pct_change().fillna(0)
    # 💡 현실적인 수익률 계산 (어제 신호 -> 오늘 매매)
    df['invested'] = df['신호'].isin(['🟢매수(Green)', '🔥역발상매수']).shift(1).fillna(0).astype(int)
    df['strat_ret'] = df['daily_ret'] * df['invested']
    df['cum_strat'] = (1 + df['strat_ret']).cumprod()
    df['cum_bah'] = (1 + df['daily_ret']).cumprod()
    return df

# ── UI 및 실행 ──
col1, col2 = st.columns([2, 1])
with col1:
    ticker = st.selectbox("종목 선택", ["QQQ", "SPY", "SOXX"])
with col2:
    start_year = st.selectbox("시작 연도", [2000, 2010, 2020])

with st.spinner("📡 데이터를 분석 중입니다..."):
    raw = load_macro_data(ticker, start_year)
    sig_df = calculate_cms_signals(raw)
    perf_df = calc_returns(sig_df, start_year)

# 📊 성과 요약 (B&H 비교 복구!)
st.markdown("#### 📊 전략 성과 요약")
m1, m2, m3, m4 = st.columns(4)
f_strat = (perf_df['cum_strat'].iloc[-1]-1)*100
f_bah = (perf_df['cum_bah'].iloc[-1]-1)*100
m1.metric("신호전략 수익률", f"{f_strat:.1f}%", delta=f"{f_strat - f_bah:.1f}%p")
m2.metric("바이앤홀드 수익률", f"{f_bah:.1f}%")
m3.metric("전략 MDD", f"{(perf_df['cum_strat']/perf_df['cum_strat'].cummax()-1).min()*100:.1f}%")
m4.metric("B&H MDD", f"{(perf_df['cum_bah']/perf_df['cum_bah'].cummax()-1).min()*100:.1f}%")

# 📈 메인 차트
st.markdown("#### 📈 가격 차트 + 신호등 배경")
fig = make_subplots(rows=2, cols=1, row_heights=[0.72, 0.28], shared_xaxes=True, vertical_spacing=0.04)

sig_color_map = {
    '🟢매수(Green)': 'rgba(16,185,129,0.15)', '🟡관망(Yellow)': 'rgba(245,158,11,0.15)', 
    '🔴도망챠(Red)': 'rgba(239,68,68,0.2)', '🔥역발상매수': 'rgba(124,58,237,0.3)'
}
dates, sigs = perf_df.index.tolist(), perf_df['신호'].tolist()
block_start, block_sig = dates[0], sigs[0]
for i in range(1, len(dates)):
    if sigs[i] != block_sig or i == len(dates) - 1:
        fig.add_vrect(x0=block_start, x1=dates[i], fillcolor=sig_color_map.get(block_sig), layer="below", line_width=0, row=1, col=1)
        block_start, block_sig = dates[i], sigs[i]

fig.add_trace(go.Scatter(x=perf_df.index, y=perf_df['Close'], name='종가', line=dict(color='#1d4ed8')), row=1, col=1)
fig.add_trace(go.Scatter(x=perf_df.index, y=perf_df['MA200'], name='200일선', line=dict(dash='dash', color='green')), row=1, col=1)
fig.add_trace(go.Scatter(x=perf_df.index, y=(perf_df['cum_strat']-1)*100, name='전략 수익률(%)'), row=2, col=1)
fig.add_trace(go.Scatter(x=perf_df.index, y=(perf_df['cum_bah']-1)*100, name='존버 수익률(%)', line=dict(dash='dot')), row=2, col=1)
st.plotly_chart(fig, use_container_width=True)

# 🎯 이벤트 검증 표 복구
st.markdown("#### 🎯 주요 이벤트 검증")
ev_cols = st.columns(2)
for i, ev in enumerate(EVENTS):
    ev_date = pd.Timestamp(ev['date'])
    available = perf_df.index[perf_df.index >= ev_date]
    if len(available) == 0: continue
    row = perf_df.loc[available[0]]
    with ev_cols[i % 2]:
        st.markdown(f"""
<div class="event-card {'ev-safe' if ev['type']=='safe' else 'ev-danger'}">
    <b>📅 {ev['date']} | {ev['name']}</b><br>
    CMS: {row['CMS']:.1f}점 | 신호: {row['신호']}
</div>
""", unsafe_allow_html=True)
