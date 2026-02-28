import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime

st.set_page_config(page_title="CMS 신호 백테스트", page_icon="🚦", layout="wide")

# ── 스타일 설정 ──
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700&display=swap');
html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; }
.block-container { padding-top: 3.5rem !important; }

.stat-card { background: #f8faff; border: 1px solid #dbeafe; border-radius: 10px; padding: 16px; text-align: center; margin-bottom: 10px; }
.stat-num  { font-size: 1.6rem; font-weight: 800; }
.stat-label{ font-size: 0.78rem; color: #6b7280; margin-top: 2px; }

.event-card { border-radius: 8px; padding: 10px 14px; margin-bottom: 8px; font-size: 0.84rem; line-height: 1.5; border-left: 4px solid; }
.ev-safe   { background:#f0fdf4; border-color:#10b981; }
.ev-danger { background:#fef2f2; border-color:#ef4444; }

.sig-green  { color: #059669; font-weight: 800; }
.sig-yellow { color: #d97706; font-weight: 800; }
.sig-red    { color: #dc2626; font-weight: 800; }
.sig-titan  { color: #7c3aed; font-weight: 800; } /* 타이탄 보라색 */
</style>
""", unsafe_allow_html=True)

st.title("🚦 CMS 통합 신호등 백테스트")
st.caption("타이탄 알파 설계도 기반: VIX(공포), OVX(전쟁), Spread(신용)를 융합한 1,000억짜리 방패 엔진입니다.")
st.markdown("---")

# ── 역사적 이벤트 정의 ──
EVENTS = [
    {"date": "2000-03-24", "name": "닷컴버블 붕괴 시작", "type": "danger", "desc": "추세 붕괴 포착. 기계적 현금화 구간"},
    {"date": "2008-09-15", "name": "리먼 파산 (금융위기)", "type": "danger", "desc": "신용 스프레드 폭발 및 🔴빨간불 지속 구간"},
    {"date": "2009-03-09", "name": "금융위기 대바닥", "type": "safe", "desc": "역발상 매수 타점(Purple) 발생 구간"},
    {"date": "2020-02-24", "name": "코로나 팬데믹 폭락", "type": "danger", "desc": "VIX 폭등에 따른 즉각적인 대피 신호"},
    {"date": "2020-03-23", "name": "코로나 최저점", "type": "safe", "desc": "역사적 V자 랠리 출발점 및 역발상 매수 신호"},
    {"date": "2022-01-05", "name": "인플레이션 & 긴축", "type": "danger", "desc": "금리차 역전 및 1년 내내 이어진 베어마켓"},
    {"date": "2025-04-02", "name": "트럼프 관세 충격", "type": "danger", "desc": "단기 노이즈에 대한 추세 방어력 테스트"}
]

# ── 데이터 로딩 ──
@st.cache_data(ttl=3600, show_spinner=False)
def load_macro_data(ticker, start_year):
    fetch_start = f"{start_year - 1}-01-01"
    
    # 1. 메인 지수
    df = yf.download(ticker, start=fetch_start, interval='1d', progress=False)
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    df = df[['Close']].rename(columns={'Close': 'Close'})
    
    # 2. VIX (공포) & OVX (전쟁)
    vix = yf.download("^VIX", start=fetch_start, interval='1d', progress=False)
    ovx = yf.download("^OVX", start=fetch_start, interval='1d', progress=False)
    
    if isinstance(vix.columns, pd.MultiIndex): vix.columns = vix.columns.get_level_values(0)
    if isinstance(ovx.columns, pd.MultiIndex): ovx.columns = ovx.columns.get_level_values(0)
    
    vix = vix[['Close']].rename(columns={'Close': 'VIX'})
    ovx = ovx[['Close']].rename(columns={'Close': 'OVX'})
    
    # 3. 금리차 (10Y-3M)
    tnx = yf.download("^TNX", start=fetch_start, interval='1d', progress=False)
    irx = yf.download("^IRX", start=fetch_start, interval='1d', progress=False)
    if isinstance(tnx.columns, pd.MultiIndex): tnx.columns = tnx.columns.get_level_values(0)
    if isinstance(irx.columns, pd.MultiIndex): irx.columns = irx.columns.get_level_values(0)
    spread = (tnx[['Close']] - irx[['Close']]).rename(columns={'Close': 'Spread'})
    
    # 병합 및 결측치 처리
    combined = df.join(vix, how='inner').join(ovx, how='left').join(spread, how='left')
    combined['OVX'] = combined['OVX'].fillna(30) # 2007년 이전 데이터 보정
    combined['Spread'] = combined['Spread'].fillna(1.0)
    combined = combined.dropna(subset=['Close', 'VIX'])
    combined.index = pd.to_datetime(combined.index).tz_localize(None)
    
    return combined

# ── CMS 시그널 계산 ──
def calculate_cms_signals(df):
    df = df.copy()
    df['MA200'] = df['Close'].rolling(200).mean()
    
    # 타이탄 알파 가중치 설정
    W_vix, W_ovx = 1.5, 2.0

    def get_status(row):
        vix, ovx, spread = row['VIX'], row['OVX'], row['Spread']
        close, ma200 = row['Close'], row['MA200']
        
        # 패널티 산출
        pen_vix = W_vix * max(0, vix - 22)
        pen_ovx = W_ovx * max(0, ovx - 35)
        pen_credit = 20 if spread < 0 else 0 
        
        cms = 100 - pen_vix - pen_ovx - pen_credit
        
        # [Titan's Secret] 역발상 매수 타점: 빨간불인데 200일선 대비 -8% 이하 급락 시
        if cms < 55 and pd.notna(ma200) and close < (ma200 * 0.92):
            return '🔥역발상매수', cms
            
        if cms >= 85: return '🟢매수(Green)', cms
        if cms >= 55: return '🟡관망(Yellow)', cms
        return '🔴도망챠(Red)', cms

    results = df.apply(get_status, axis=1, result_type='expand')
    df['신호'], df['CMS'] = results[0], results[1]
    return df

# ── 수익률 계산 (타임머신 버그 수정 반영) ──
def calc_strategy_return(df, start_year):
    df = df.copy()
    start_dt = f"{start_year}-01-01"
    df = df[df.index >= start_dt]
    
    df['daily_ret'] = df['Close'].pct_change().fillna(0)
    
    # 💡 소장님이 수정하신 실전 로직: "어제 신호로 오늘 매매"
    df['invested'] = df['신호'].isin(['🟢매수(Green)', '🔥역발상매수']).shift(1).fillna(0).astype(int)
    
    df['strat_ret'] = df['daily_ret'] * df['invested']
    df['cum_bah'] = (1 + df['daily_ret']).cumprod()
    df['cum_strat'] = (1 + df['strat_ret']).cumprod()
    return df

# ── UI 구성 ──
col_opt1, col_opt2 = st.columns([2, 1])
with col_opt1:
    ticker_map = {'NASDAQ (QQQ)': 'QQQ', 'S&P500 (SPY)': 'SPY', '반도체 (SOXX)': 'SOXX'}
    selected_name = st.selectbox("분석 종목 (3대 지수)", list(ticker_map.keys()))
    ticker = ticker_map[selected_name]
with col_opt2:
    start_year = st.selectbox("시작 연도", [2000, 2005, 2008, 2010, 2015, 2020], index=0)

with st.spinner("📡 CMS 신호등 엔진 백테스트 구동 중..."):
    raw_df = load_macro_data(ticker, start_year)

if raw_df.empty or len(raw_df) < 300:
    st.error("데이터가 부족합니다.")
    st.stop()

sig_df = calculate_cms_signals(raw_df)
perf_df = calc_strategy_return(sig_df, start_year)

# ── 성과 요약 ──
final_bah = round((perf_df['cum_bah'].iloc[-1] - 1) * 100, 1)
final_strat = round((perf_df['cum_strat'].iloc[-1] - 1) * 100, 1)
mdd_bah = round(((perf_df['cum_bah'] / perf_df['cum_bah'].cummax() - 1).min()) * 100, 1)
mdd_strat = round(((perf_df['cum_strat'] / perf_df['cum_strat'].cummax() - 1).min()) * 100, 1)

st.markdown("#### 📊 CMS 가중치 전략 성과 요약 (현실 데이터)")
m1, m2, m3, m4 = st.columns(4)
m1.metric("신호전략 수익률", f"{final_strat:+.1f}%", delta=f"{final_strat - final_bah:+.1f}%p")
m2.metric("바이앤홀드 수익률", f"{final_bah:+.1f}%")
m3.metric("전략 최대낙폭(MDD)", f"{mdd_strat:.1f}%")
m4.metric("B&H 최대낙폭(MDD)", f"{mdd_bah:.1f}%")

# ── 메인 차트 ──
st.markdown("#### 📈 가격 차트 + CMS 신호등 배경")
fig = make_subplots(rows=2, cols=1, row_heights=[0.72, 0.28], shared_xaxes=True, vertical_spacing=0.04)

sig_color_map = {
    '🟢매수(Green)': 'rgba(16,185,129,0.15)', 
    '🟡관망(Yellow)': 'rgba(245,158,11,0.15)', 
    '🔴도망챠(Red)': 'rgba(239,68,68,0.2)',
    '🔥역발상매수': 'rgba(124,58,237,0.3)'
}
dates = perf_df.index.tolist()
sigs  = perf_df['신호'].tolist()

if len(dates) > 0:
    block_start, block_sig = dates[0], sigs[0]
    for i in range(1, len(dates)):
        if sigs[i] != block_sig or i == len(dates) - 1:
            fig.add_vrect(x0=block_start, x1=dates[i], fillcolor=sig_color_map.get(block_sig, 'rgba(0,0,0,0)'), layer="below", line_width=0, row=1, col=1)
            block_start, block_sig = dates[i], sigs[i]

fig.add_trace(go.Scatter(x=perf_df.index, y=perf_df['Close'], name='종가', line=dict(color='#1d4ed8', width=1.8)), row=1, col=1)
fig.add_trace(go.Scatter(x=perf_df.index, y=perf_df['MA200'], name='200일선', line=dict(color='#047857', width=1.5, dash='dash')), row=1, col=1)

# 전략 누적 수익률 차트
fig.add_trace(go.Scatter(x=perf_df.index, y=(perf_df['cum_strat'] - 1) * 100, name='CMS 신호전략', line=dict(color='#2563eb', width=2)), row=2, col=1)
fig.add_trace(go.Scatter(x=perf_df.index, y=(perf_df['cum_bah'] - 1) * 100, name='바이앤홀드', line=dict(color='#9ca3af', width=1.5, dash='dash')), row=2, col=1)

fig.update_layout(height=650, template='plotly_white', hovermode='x unified', margin=dict(l=10, r=10, t=60, b=10))
st.plotly_chart(fig, use_container_width=True)

# ── 이벤트 검증 ──
st.markdown("#### 🎯 주요 역사적 이벤트 CMS 검증")
ev_cols = st.columns(2)
for i, ev in enumerate(EVENTS):
    ev_date = pd.Timestamp(ev['date'])
    available = perf_df.index[perf_df.index >= ev_date]
    if len(available) == 0: continue
    closest = available[0]
    row = perf_df.loc[closest]
    sig = row['신호']
    
    with ev_cols[i % 2]:
        st.markdown(f"""
<div class="event-card {'ev-safe' if ev['type']=='safe' else 'ev-danger'}">
    <div style="font-weight:700;">📅 {ev['date']} | {ev['name']}</div>
    <div>CMS 점수: <b>{row['CMS']:.1f}점</b> | 신호: <b>{sig}</b></div>
    <div style="font-size:0.8rem; color:#4b5563;">{ev['desc']}</div>
</div>
""", unsafe_allow_html=True)
