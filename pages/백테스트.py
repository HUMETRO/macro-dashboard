import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import yfinance as yf

st.set_page_config(page_title="V8 최종 하이브리드 검증", page_icon="🚦", layout="wide")

# ── 스타일 설정 ──
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700&display=swap');
html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; }
.event-card { border-radius: 8px; padding: 12px 16px; margin-bottom: 10px; font-size: 0.9rem; border-left: 5px solid; }
.ev-safe { background:#f0fdf4; border-color:#10b981; color: #166534; }
.ev-danger { background:#fef2f2; border-color:#ef4444; color: #991b1b; }
</style>
""", unsafe_allow_html=True)

st.title("🚦 V8 최종 하이브리드: 레버리지 안정화 버전")
st.caption("레버리지 종목의 상장 전 데이터 공백에 따른 수익률 오류를 완벽히 해결한 최종 모델입니다.")

# ── 7대 역사적 위기 리스트 (데이터가 있는 경우에만 표시됨) ──
EVENTS = [
    {"date": "2000-03-24", "name": "닷컴버블 붕괴", "type": "danger", "desc": "나스닥 -80% 하락 대피 테스트"},
    {"date": "2008-09-15", "name": "리먼 브라더스 파산", "type": "danger", "desc": "금융위기 정점 대응력"},
    {"date": "2009-03-09", "name": "금융위기 대바닥", "type": "safe", "desc": "공포 속의 역발상 매수(Purple)"},
    {"date": "2011-08-08", "name": "미국 신용등급 강등", "type": "danger", "desc": "단기 폭락장 세이프가드 작동"},
    {"date": "2018-12-24", "name": "미중 무역전쟁 바닥", "type": "safe", "desc": "하락 추세 끝자락의 매수 신호"},
    {"date": "2020-02-24", "name": "코로나 팬데믹 쇼크", "type": "danger", "desc": "VIX Spike 조기경보의 핵심"},
    {"date": "2022-01-05", "name": "인플레이션 하락장", "type": "danger", "desc": "1년 내내 이어진 하락장 회피"}
]

# ── 데이터 로딩 (공백 방지 로직 강화) ──
@st.cache_data(ttl=3600, show_spinner=False)
def load_safe_data(ticker, start_year):
    fetch_start = f"{start_year - 1}-01-01"
    df = yf.download(ticker, start=fetch_start, interval='1d', progress=False)
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    df = df[['Close']].dropna()
    
    vix = yf.download("^VIX", start=fetch_start, progress=False)
    ovx = yf.download("^OVX", start=fetch_start, progress=False)
    tnx = yf.download("^TNX", start=fetch_start, progress=False)
    irx = yf.download("^IRX", start=fetch_start, progress=False)
    for d in [vix, ovx, tnx, irx]:
        if isinstance(d.columns, pd.MultiIndex): d.columns = d.columns.get_level_values(0)
        
    combined = df.join(vix['Close'].to_frame('VIX'), how='inner')
    combined = combined.join(ovx['Close'].to_frame('OVX'), how='left')
    combined['Spread'] = (tnx['Close'] - irx['Close'])
    combined['MA20'] = combined['Close'].rolling(20).mean()
    combined['MA50'] = combined['Close'].rolling(50).mean()
    combined['MA200'] = combined['Close'].rolling(200).mean()
    combined['VIX_MA5'] = combined['VIX'].rolling(5).mean()
    
    combined['OVX'] = combined['OVX'].fillna(30)
    combined['Spread'] = combined['Spread'].fillna(1.0)
    # 데이터가 실제로 있는 구간만 슬라이싱 (여기서 오류 차단)
    return combined.dropna(subset=['Close', 'VIX', 'MA200']).tz_localize(None)

# ── 판정 로직 ──
def calculate_signals(df, ticker):
    df = df.copy()
    is_lev = any(x in ticker for x in ["TQQQ", "QLD", "SOXL", "UPRO"])
    
    def get_status(row):
        c, m20, m50, m200 = row['Close'], row['MA20'], row['MA50'], row['MA200']
        v, v_ma5, o, s = row['VIX'], row['VIX_MA5'], row['OVX'], row['Spread']
        mult = 2.5 if (is_lev and c < m50) else (2.0 if c < m50 else 1.0)
        pen = ((1.0 * max(0, v - 25)) + (1.2 * max(0, o - 35)) + (20 if s < -0.5 else 0)) * mult
        cms = 100 - pen
        v_spike = v / v_ma5 > 1.25 if v_ma5 > 0 else False
        
        if c < m200 and cms < 45: return '🔴전략적철수(Red)', cms
        if is_lev:
            if c < m20 or v_spike: return '⚠️초정밀경보(Turbo)', cms
        else:
            if c < m50 or v_spike: return '🟡조기경보(Yellow)', cms
        if cms >= 55: return '🟢매수(Green)', cms
        if c < (m200 * 0.90): return '🔥역발상매수', cms
        return '🟡안전관망(Yellow)', cms

    res = df.apply(get_status, axis=1, result_type='expand')
    df['신호'], df['CMS'] = res[0], res[1]
    return df

# ── 성과 계산 ──
def calc_safe_performance(df, ticker, start_year):
    # 실제 데이터가 시작되는 시점부터 계산
    actual_start = df.index[df.index >= f"{start_year}-01-01"]
    if len(actual_start) == 0: return None
    df = df[df.index >= actual_start[0]].copy()
    
    df['daily_ret'] = df['Close'].pct_change().fillna(0)
    is_lev = any(x in ticker for x in ["TQQQ", "QLD", "SOXL", "UPRO"])

    def get_exp(sig):
        if sig == '🟢매수(Green)': return 1.0
        if sig == '⚠️초정밀경보(Turbo)': return 0.2 if is_lev else 0.4
        if sig == '🟡조기경보(Yellow)': return 0.4
        if sig == '🟡안전관망(Yellow)': return 0.7
        if sig == '🔥역발상매수': return 0.8
        return 0.0

    df['base_exp'] = df['신호'].apply(get_exp).shift(1).fillna(0)
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

# ── 메인 실행 ──
ticker = st.selectbox("종목 선택", ["QQQ", "SOXX", "TQQQ", "SOXL", "SPY"])
start_year = st.selectbox("시작 연도", [2000, 2010, 2020])

raw_data = load_safe_data(ticker, start_year)
sig_df = calculate_signals(raw_data, ticker)
perf_df = calc_safe_performance(sig_df, ticker, start_year)

if perf_df is not None:
    f_strat, f_bah = (perf_df['cum_strat'].iloc[-1]-1)*100, (perf_df['cum_bah'].iloc[-1]-1)*100
    mdd_strat = (perf_df['cum_strat']/perf_df['cum_strat'].cummax()-1).min()*100
    mdd_bah = (perf_df['cum_bah']/perf_df['cum_bah'].cummax()-1).min()*100

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("전략 수익률", f"{f_strat:,.1f}%", delta=f"{f_strat - f_bah:,.1f}%p")
    m2.metric("존버(B&H) 수익률", f"{f_bah:,.1f}%")
    m3.metric("전략 MDD", f"{mdd_strat:.1f}%", delta=f"B&H대비 {abs(mdd_bah)-abs(mdd_strat):.1f}%p 우수")
    m4.metric("존버(B&H) MDD", f"{mdd_bah:.1f}%")

    # 차트
    fig = make_subplots(rows=2, cols=1, row_heights=[0.7, 0.3], shared_xaxes=True)
    fig.add_trace(go.Scatter(x=perf_df.index, y=perf_df['Close'], name='Price'), row=1, col=1)
    fig.add_trace(go.Scatter(x=perf_df.index, y=(perf_df['cum_strat']-1)*100, name='전략'), row=2, col=1)
    fig.add_trace(go.Scatter(x=perf_df.index, y=(perf_df['cum_bah']-1)*100, name='B&H', line=dict(dash='dot')), row=2, col=1)
    st.plotly_chart(fig, use_container_width=True)

    # 🎯 위기 검증표 (종목 데이터가 존재하는 기간만 표시)
    st.markdown("#### 🎯 역사적 위기 회피 검증")
    ev_cols = st.columns(2)
    for i, ev in enumerate(EVENTS):
        ev_date = pd.Timestamp(ev['date'])
        if ev_date < perf_df.index[0]: continue
        row = perf_df.loc[perf_df.index >= ev_date].iloc[0]
        sig = row['신호']
        sig_color = "red" if "철수" in sig else ("orange" if "경보" in sig or "관망" in sig else "green")
        if "역발상" in sig: sig_color = "purple"
        with ev_cols[i % 2]:
            st.markdown(f'<div class="event-card {"ev-safe" if ev["type"]=="safe" else "ev-danger"}"><b>📅 {ev["date"]} | {ev["name"]}</b><br>신호: <span style="color:{sig_color}; font-weight:800;">{sig}</span><br><small>{ev["desc"]}</small></div>', unsafe_allow_html=True)
else:
    st.error("선택한 연도에는 해당 종목의 데이터가 없습니다. 시작 연도를 조정해 주세요!")
