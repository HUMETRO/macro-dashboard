import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime

st.set_page_config(page_title="순수 추세추종 백테스트", page_icon="📈", layout="wide")

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
.ev-watch  { background:#fffbeb; border-color:#f59e0b; }

.signal-buy  { color: #059669; font-weight: 800; }
.signal-sell { color: #dc2626; font-weight: 800; }
.signal-wait { color: #d97706; font-weight: 800; }
</style>
""", unsafe_allow_html=True)

st.title("📈 투자의 규칙(CAN SLIM) 모멘텀 백테스트")
st.caption("매크로 지표의 간섭을 배제하고, 오직 가격 추세(L-S 스코어)에만 집중하여 하락은 피하고 상승은 끝까지 먹는 실전 엔진입니다. (타임머신 버그 수정 완료)")
st.markdown("---")

EVENTS = [
    {"date": "2000-03-24", "name": "닷컴버블 붕괴 시작", "type": "danger", "desc": "추세 붕괴. 기계적 손절을 통한 자산 보호 구역"},
    {"date": "2002-10-09", "name": "닷컴버블 최저점", "type": "safe", "desc": "긴 하락장 종료 후 새로운 강세장(팔로우 스루) 시작"},
    {"date": "2008-09-15", "name": "리먼 파산 (금융위기)", "type": "danger", "desc": "L/S 스코어 전면 붕괴. 완벽한 도망챠 구간"},
    {"date": "2009-03-09", "name": "금융위기 대바닥", "type": "safe", "desc": "강한 반등 모멘텀 발생. 새로운 주도주 랠리 시작"},
    {"date": "2015-08-24", "name": "중국 위안화 쇼크", "type": "danger", "desc": "단기 모멘텀 급락에 따른 기계적 회피"},
    {"date": "2018-10-10", "name": "미중 무역전쟁 폭락", "type": "danger", "desc": "추세 꺾임. 4분기 내내 현금 보유로 방어"},
    {"date": "2020-02-24", "name": "코로나 팬데믹 폭락", "type": "danger", "desc": "역사상 가장 빠른 속도의 추세 붕괴. 즉각 대피"},
    {"date": "2020-04-06", "name": "코로나 V자 반등 확인", "type": "safe", "desc": "S-score(단기 기세) 강한 양수 전환. 칼같은 재탑승"},
    {"date": "2022-01-05", "name": "인플레이션 & 긴축", "type": "danger", "desc": "1년 내내 이어진 하락 추세. 철저한 관망 유지"},
    {"date": "2025-04-02", "name": "트럼프 관세 충격", "type": "danger", "desc": "단기 노이즈에 대한 추세 방어력 테스트"}
]

@st.cache_data(ttl=3600, show_spinner=False)
def load_price_data(ticker, start_year):
    # 추세 계산을 위해 1년 전 데이터부터 미리 당겨옴 (200일선 등 계산용)
    fetch_start = f"{start_year - 1}-01-01"
    df = yf.download(ticker, start=fetch_start, interval='1d', progress=False)
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    df = df[['Close']].rename(columns={'Close': 'Close'})
    df.index = pd.to_datetime(df.index).tz_localize(None)
    return df

def calculate_pure_signals(df):
    close = df['Close']
    
    # ── L-score (장기 체력) ──
    ma200 = close.rolling(200).mean()
    ma200_dist = (close / ma200 - 1).fillna(0)
    high_52w = close.rolling(252).max()
    low_52w = close.rolling(252).min()
    range_52w = (high_52w - low_52w).replace(0, np.nan)
    pos_52w = ((close - low_52w) / range_52w).fillna(0.5)
    ret_6m = close.pct_change(126).fillna(0)
    l_score = ma200_dist * 0.4 + pos_52w * 0.3 + ret_6m * 0.3

    # ── S-score (단기 기세) ──
    ma20 = close.rolling(20).mean()
    ma20_dist = (close / ma20 - 1).fillna(0)
    ret_1m = close.pct_change(21).fillna(0)
    vol = close.pct_change().rolling(20).std().fillna(0)
    s_score = ma20_dist * 0.5 + ret_1m * 0.4 - vol * 0.1

    # 💡 순수 갈가니/미너비니 추세 로직
    def get_sig(row):
        l = row['L']
        s = row['S']
        
        # 장기, 단기가 모두 살아있으면 강세장 -> 매수 (Go)
        if l > 0 and s > 0: 
            return '매수'
        
        # 단기 모멘텀이 꺾이면 즉시 손절 및 방어 -> 도망챠 (Stop)
        if s < -0.01: 
            return '도망챠'
            
        # 그 외의 애매한 구간은 현금 들고 지켜봄 -> 관망 (Wait)
        return '관망'

    result = pd.DataFrame({'Close': close, 'L': l_score, 'S': s_score})
    result['신호'] = result.apply(get_sig, axis=1)
    
    # 데이터 공백(200일)이 있는 구간을 제거하여 정확한 시작 시점을 맞춤
    return result.dropna()

def calc_strategy_return(df, start_year):
    df = df.copy()
    
    # 유저가 선택한 진짜 시작 연도부터 데이터를 자름 (B&H 기준점 완벽 일치)
    start_dt = f"{start_year}-01-01"
    df = df[df.index >= start_dt]
    
    df['daily_ret'] = df['Close'].pct_change().fillna(0)
    
    # 💡 타임머신 버그 해결: 오늘 장 마감 신호로 '내일'의 수익률을 먹는다 (.shift(1))
    df['invested'] = (df['신호'] == '매수').shift(1).fillna(0).astype(int)
    
    df['strat_ret'] = df['daily_ret'] * df['invested']
    df['cum_bah'] = (1 + df['daily_ret']).cumprod()
    df['cum_strat'] = (1 + df['strat_ret']).cumprod()
    
    return df

col_opt1, col_opt2 = st.columns([2, 1])
with col_opt1:
    ticker_map = {'NASDAQ (QQQ)': 'QQQ', 'S&P500 (SPY)': 'SPY', '반도체 (SOXX)': 'SOXX'}
    selected_name = st.selectbox("분석 종목 (3대 지수)", list(ticker_map.keys()))
    ticker = ticker_map[selected_name]
with col_opt2:
    start_year = st.selectbox("시작 연도", [2000, 2005, 2008, 2010, 2015, 2020], index=0)

with st.spinner("📡 퓨어 모멘텀 엔진 백테스트 구동 중..."):
    raw_df = load_price_data(ticker, start_year)

if raw_df.empty or len(raw_df) < 300:
    st.error("데이터가 부족합니다.")
    st.stop()

# 1. 시그널 계산 (과거 1년 전 데이터 활용하여 초기 200일선 확보)
sig_df = calculate_pure_signals(raw_df)

# 2. 수익률 계산 (정확히 유저가 선택한 시작 연도부터 수익률 경쟁 시작)
perf_df = calc_strategy_return(sig_df, start_year)

final_bah   = round((perf_df['cum_bah'].iloc[-1]   - 1) * 100, 1)
final_strat = round((perf_df['cum_strat'].iloc[-1] - 1) * 100, 1)
mdd_bah     = round(((perf_df['cum_bah']   / perf_df['cum_bah'].cummax()   - 1).min()) * 100, 1)
mdd_strat   = round(((perf_df['cum_strat'] / perf_df['cum_strat'].cummax() - 1).min()) * 100, 1)

st.markdown("#### 📊 투자의 규칙 전략 성과 요약 (타임머신 오류 100% 제거)")
m1, m2, m3, m4 = st.columns(4)

# 💡 수익률이 B&H를 이겼을 때 색상 강조
strat_color = "normal" if final_strat >= final_bah else "off"
m1.metric("신호전략 수익률", f"{final_strat:+.1f}%", delta=f"B&H 대비 {(final_strat - final_bah):+.1f}%p", delta_color=strat_color)
m2.metric("바이앤홀드 수익률", f"{final_bah:+.1f}%")
m3.metric("전략 최대낙폭(MDD)", f"{mdd_strat:.1f}%")
m4.metric("B&H 최대낙폭(MDD)", f"{mdd_bah:.1f}%")
st.markdown("---")

st.markdown("#### 📈 가격 차트 + 신호 배경 (순수 모멘텀)")
fig = make_subplots(rows=2, cols=1, row_heights=[0.72, 0.28], shared_xaxes=True, vertical_spacing=0.04)

sig_color_map = {
    '매수': 'rgba(16,185,129,0.15)', 
    '관망': 'rgba(245,158,11,0.15)', 
    '도망챠': 'rgba(239,68,68,0.2)'
}
dates = perf_df.index.tolist()
sigs  = perf_df['신호'].tolist()

if len(dates) > 0:
    block_start, block_sig = dates[0], sigs[0]
    for i in range(1, len(dates)):
        if sigs[i] != block_sig or i == len(dates) - 1:
            fig.add_vrect(x0=block_start, x1=dates[i], fillcolor=sig_color_map.get(block_sig, 'rgba(0,0,0,0)'), layer="below", line_width=0, row=1, col=1)
            block_start, block_sig = dates[i], sigs[i]

fig.add_trace(go.Scatter(x=perf_df.index, y=perf_df['Close'], name=ticker, line=dict(color='#1d4ed8', width=1.8)), row=1, col=1)

# 200일선 차트에 추가
fig.add_trace(go.Scatter(x=perf_df.index, y=sig_df.loc[perf_df.index, 'MA200'], name='200일선', line=dict(color='#047857', width=1.5, dash='dash')), row=1, col=1)

for ev in EVENTS:
    ev_date = pd.Timestamp(ev['date'])
    if ev_date < perf_df.index[0] or ev_date > perf_df.index[-1]: continue
    color = '#dc2626' if ev['type'] == 'danger' else '#059669'
    fig.add_vline(x=ev_date, line_dash="dot", line_color=color, line_width=1.5, row=1, col=1)
    fig.add_annotation(x=ev_date, y=1.02, xref='x', yref='paper', text=ev['name'][:6], showarrow=False, font=dict(size=9, color=color), textangle=-60, xanchor='left')

fig.add_trace(go.Scatter(x=perf_df.index, y=(perf_df['cum_strat'] - 1) * 100, name='추세전략 누적수익', line=dict(color='#2563eb', width=2)), row=2, col=1)
