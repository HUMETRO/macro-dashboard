import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime

st.set_page_config(page_title="신호 백테스트", page_icon="🔬", layout="wide")

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

.signal-buy  { color: #059669; font-weight: 700; }
.signal-sell { color: #dc2626; font-weight: 700; }
.signal-wait { color: #d97706; font-weight: 700; }
</style>
""", unsafe_allow_html=True)

st.title("🔬 위험알리미 신호 백테스트 (VIX 방어 탑재)")
st.caption("과거 데이터에 S-L 스코어와 VIX(공포지수) 로직을 결합하여 매수/도망챠 신호의 신뢰도를 검증합니다.")
st.markdown("---")

# 💡 닷컴버블부터 트럼프 관세까지 완벽 정리!
EVENTS = [
    {"date": "2000-03-24", "name": "닷컴버블 붕괴 시작", "type": "danger", "desc": "나스닥 고점 형성 후 200일선 붕괴. -80% 지옥의 시작"},
    {"date": "2002-10-09", "name": "닷컴버블 최저점", "type": "safe", "desc": "거품이 완전히 꺼진 후 형성된 역사적 대바닥"},
    {"date": "2008-09-15", "name": "리먼 파산 (금융위기)", "type": "danger", "desc": "QQQ 200일선 완벽 붕괴. 글로벌 금융 시스템 마비"},
    {"date": "2009-03-09", "name": "금융위기 대바닥", "type": "safe", "desc": "연준 양적완화. 200일선 아래에서 극적인 V자 반등 시작"},
    {"date": "2011-08-05", "name": "미국 신용등급 강등", "type": "danger", "desc": "QQQ 200일선 하향 돌파. 유럽발 재정 위기 겹침"},
    {"date": "2015-08-24", "name": "중국 위안화 쇼크", "type": "danger", "desc": "중국발 공포로 나스닥 200일선 붕괴 및 블랙먼데이"},
    {"date": "2018-10-10", "name": "미중 무역전쟁 폭락", "type": "danger", "desc": "200일선 붕괴 후 12월까지 이어지는 끔찍한 하락장"},
    {"date": "2020-02-24", "name": "코로나 팬데믹 폭락", "type": "danger", "desc": "역사상 가장 빠른 속도로 QQQ 200일선 수직 붕괴"},
    {"date": "2020-03-23", "name": "코로나 최저점", "type": "safe", "desc": "무제한 양적완화 발표. 역사적 V자 랠리 출발점"},
    {"date": "2022-01-05", "name": "인플레이션 & 긴축", "type": "danger", "desc": "QQQ 200일선 붕괴. 이후 1년 내내 이어진 베어마켓"},
    {"date": "2022-10-13", "name": "22년 하락장 바닥", "type": "safe", "desc": "인플레이션 피크아웃 확인 및 기나긴 하락 추세 종료"},
    {"date": "2025-04-02", "name": "트럼프 관세 충격", "type": "danger", "desc": "단기 발작으로 QQQ 200일선 위협. 소장님의 V자 반등 포착 구간"}
]

@st.cache_data(ttl=3600, show_spinner=False)
def load_backtest_data(ticker, start_year):
    start = f"{start_year}-01-01"
    df = yf.download(ticker, start=start, interval='1d', progress=False)
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    df = df[['Close']].rename(columns={'Close': 'Close'})
    
    vix_df = yf.download("^VIX", start=start, interval='1d', progress=False)
    if isinstance(vix_df.columns, pd.MultiIndex): vix_df.columns = vix_df.columns.get_level_values(0)
    vix_df = vix_df[['Close']].rename(columns={'Close': 'VIX'})
    
    combined = df.join(vix_df, how='inner').dropna()
    combined.index = pd.to_datetime(combined.index).tz_localize(None)
    return combined

def calculate_signals(df):
    close, vix = df['Close'], df['VIX']
    
    ma200 = close.rolling(200).mean()
    ma200_dist = (close / ma200 - 1).fillna(0)
    high_52w = close.rolling(252).max()
    low_52w = close.rolling(252).min()
    range_52w = (high_52w - low_52w).replace(0, np.nan)
    pos_52w = ((close - low_52w) / range_52w).fillna(0.5)
    ret_6m = close.pct_change(126).fillna(0)
    l_score = ma200_dist * 0.4 + pos_52w * 0.3 + ret_6m * 0.3

    ma20 = close.rolling(20).mean()
    ma20_dist = (close / ma20 - 1).fillna(0)
    ret_1m = close.pct_change(21).fillna(0)
    vol = close.pct_change().rolling(20).std().fillna(0)
    s_score = ma20_dist * 0.5 + ret_1m * 0.4 - vol * 0.1

    def get_sig(row):
        l, s, v = row['L'], row['S'], row['VIX']
        if v >= 30: return '도망챠'  # VIX 강제 탈출 필터
        if s < 0: return '도망챠'    # 미너비니 필터
        if l > 0 and s > 0: return '매수'
        if l < 0 and s < 0: return '도망챠'
        return '관망'

    result = pd.DataFrame({'Close': close, 'VIX': vix, 'L': l_score, 'S': s_score}).dropna()
    result['신호'] = result.apply(get_sig, axis=1)
    return result

def find_signal_changes(df):
    changes, prev = [], None
    for dt, row in df.iterrows():
        sig = row['신호']
        if sig != prev:
            if prev is not None:
                changes.append({'date': dt, 'from': prev, 'to': sig, 'price': round(float(row['Close']), 2)})
            prev = sig
    return changes

def calc_strategy_return(df):
    df = df.copy()
    df['daily_ret'] = df['Close'].pct_change().fillna(0)
    df['invested'] = (df['신호'] == '매수').astype(int)
    df['strat_ret'] = df['daily_ret'] * df['invested']
    df['cum_bah'] = (1 + df['daily_ret']).cumprod()
    df['cum_strat'] = (1 + df['strat_ret']).cumprod()
    return df

col_opt1, col_opt2 = st.columns([2, 1])
with col_opt1:
    ticker_map = {'NASDAQ (QQQ)': 'QQQ', 'S&P500 (SPY)': 'SPY', '반도체 (SOXX)': 'SOXX'}
    selected_name = st.selectbox("분석 종목", list(ticker_map.keys()))
    ticker = ticker_map[selected_name]
with col_opt2:
    # 💡 2000년 옵션 추가!
    start_year = st.selectbox("시작 연도", [2000, 2005, 2008, 2010, 2015, 2020], index=0)

with st.spinner("📡 퀀트 엔진 백테스트 구동 중... (데이터 다운로드에 약간의 시간이 소요될 수 있습니다)"):
    raw_df = load_backtest_data(ticker, start_year)

if raw_df.empty or len(raw_df) < 300:
    st.error("데이터가 부족합니다.")
    st.stop()

sig_df  = calculate_signals(raw_df)
perf_df = calc_strategy_return(sig_df)
changes = find_signal_changes(sig_df)

final_bah   = round((perf_df['cum_bah'].iloc[-1]   - 1) * 100, 1)
final_strat = round((perf_df['cum_strat'].iloc[-1] - 1) * 100, 1)
mdd_bah     = round(((perf_df['cum_bah']   / perf_df['cum_bah'].cummax()   - 1).min()) * 100, 1)
mdd_strat   = round(((perf_df['cum_strat'] / perf_df['cum_strat'].cummax() - 1).min()) * 100, 1)

st.markdown("#### 📊 전략 성과 요약 (VIX 30 돌파 시 강제 회피 룰 적용)")
m1, m2, m3, m4 = st.columns(4)
m1.metric("신호전략 수익률", f"{final_strat:+.1f}%")
m2.metric("바이앤홀드 수익률", f"{final_bah:+.1f}%")
m3.metric("전략 최대낙폭(MDD)", f"{mdd_strat:.1f}%")
m4.metric("B&H 최대낙폭(MDD)", f"{mdd_bah:.1f}%")
st.markdown("---")

st.markdown("#### 📈 가격 차트 + 신호 배경")
fig = make_subplots(rows=2, cols=1, row_heights=[0.72, 0.28], shared_xaxes=True, vertical_spacing=0.04)

sig_color_map = {'매수': 'rgba(16,185,129,0.12)', '관망': 'rgba(245,158,11,0.12)', '도망챠': 'rgba(239,68,68,0.15)'}
dates = sig_df.index.tolist()
sigs  = sig_df['신호'].tolist()

block_start, block_sig = dates[0], sigs[0]
for i in range(1, len(dates)):
    if sigs[i] != block_sig or i == len(dates) - 1:
        fig.add_vrect(x0=block_start, x1=dates[i], fillcolor=sig_color_map[block_sig], layer="below", line_width=0, row=1, col=1)
        block_start, block_sig = dates[i], sigs[i]

fig.add_trace(go.Scatter(x=sig_df.index, y=sig_df['Close'], name=ticker, line=dict(color='#1d4ed8', width=1.8)), row=1, col=1)

for ev in EVENTS:
    ev_date = pd.Timestamp(ev['date'])
    if ev_date < sig_df.index[0] or ev_date > sig_df.index[-1]: continue
    color = '#dc2626' if ev['type'] == 'danger' else '#059669'
    fig.add_vline(x=ev_date, line_dash="dot", line_color=color, line_width=1.5, row=1, col=1)
    fig.add_annotation(x=ev_date, y=1.02, xref='x', yref='paper', text=ev['name'][:6], showarrow=False, font=dict(size=9, color=color), textangle=-60, xanchor='left')

fig.add_trace(go.Scatter(x=perf_df.index, y=(perf_df['cum_strat'] - 1) * 100, name='신호전략', line=dict(color='#2563eb', width=2)), row=2, col=1)
fig.add_trace(go.Scatter(x=perf_df.index, y=(perf_df['cum_bah'] - 1) * 100, name='바이앤홀드', line=dict(color='#9ca3af', width=1.5, dash='dash')), row=2, col=1)
fig.add_hline(y=0, line_dash='dot', line_color='#d1d5db', row=2, col=1)

fig.update_layout(height=650, template='plotly_white', hovermode='x unified', margin=dict(l=10, r=10, t=60, b=10))
st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

st.markdown("#### 🎯 주요 역사적 이벤트 신호 검증")
ev_cols = st.columns(2)
for i, ev in enumerate(EVENTS):
    ev_date = pd.Timestamp(ev['date'])
    available = sig_df.index[sig_df.index >= ev_date]
    if len(available) == 0: continue
    closest = available[0]
    row = sig_df.loc[closest]
    sig = row['신호']

    sig_class = {'매수': 'signal-buy', '관망': 'signal-wait', '도망챠': 'signal-sell'}[sig]
    ev_class  = 'ev-safe' if ev['type'] == 'safe' else 'ev-danger'

    fut_30 = sig_df.index[sig_df.index >= closest + pd.Timedelta(days=30)]
    fut_90 = sig_df.index[sig_df.index >= closest + pd.Timedelta(days=90)]
    ret_30 = f"{((sig_df.loc[fut_30[0],'Close'] / row['Close'] - 1)*100):.1f}%" if len(fut_30) else "N/A"
    ret_90 = f"{((sig_df.loc[fut_90[0],'Close'] / row['Close'] - 1)*100):.1f}%" if len(fut_90) else "N/A"

    verdict = ""
    if ev['type'] == 'danger' and sig == '도망챠': verdict = "✅ 위기 회피 성공"
    elif ev['type'] == 'danger' and sig == '매수': verdict = "❌ 위기 미감지 (투자 중)"
    elif ev['type'] == 'danger' and sig == '관망': verdict = "⚠️ 관망 중 (부분 회피)"
    elif ev['type'] == 'safe'   and sig == '매수': verdict = "✅ 상승 탑승 성공"
    elif ev['type'] == 'safe'   and sig != '매수': verdict = "⚠️ 상승 탑승 지연"

    with ev_cols[i % 2]:
        st.markdown(f"""
<div class="event-card {ev_class}">
    <div style="font-weight:700; margin-bottom:4px;">📅 {ev['date']} &nbsp;|&nbsp; {ev['name']}</div>
    <div style="color:#4b5563; margin-bottom:6px; font-size:0.8rem;">{ev['desc']}</div>
    <div>신호: <span class="{sig_class}">{sig}</span> &nbsp;|&nbsp; 1개월 후: <b>{ret_30}</b> &nbsp;|&nbsp; 3개월 후: <b>{ret_90}</b></div>
    <div style="margin-top:5px; font-weight:600;">{verdict}</div>
</div>
""", unsafe_allow_html=True)
