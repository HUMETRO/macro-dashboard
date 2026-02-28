import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import yfinance as yf

st.set_page_config(page_title="V8-Turbo 레버리지 백테스트", page_icon="🏎️", layout="wide")

# ── 스타일 설정 ──
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700&display=swap');
html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; }
.v8-header { background: linear-gradient(135deg, #0f172a, #1e40af); padding: 25px; border-radius: 12px; color: white; margin-bottom: 30px; border: 1px solid #3b82f6; }
.event-card { border-radius: 8px; padding: 12px 16px; margin-bottom: 10px; font-size: 0.9rem; border-left: 5px solid; }
.ev-safe   { background:#f0fdf4; border-color:#10b981; color: #166534; }
.ev-danger { background:#fef2f2; border-color:#ef4444; color: #991b1b; }
</style>
<div class="v8-header">
    <h1 style="margin:0;">🏎️ V8-Turbo: 레버리지 초정밀 방어 시스템</h1>
    <p style="margin:5px 0 0 0; opacity:0.8;">TQQQ / QLD / SOXL 전용 | 20일선 조기 반응 및 위기 검증 시스템</p>
</div>
""", unsafe_allow_html=True)

# ── 역사적 위기 리스트 (레버리지 관점) ──
EVENTS = [
    {"date": "2011-08-08", "name": "미국 신용등급 강등", "type": "danger", "desc": "TQQQ 초기 최대 시련. 조기경보 작동 여부?"},
    {"date": "2015-08-24", "name": "중국 위안화 쇼크", "type": "danger", "desc": "글로벌 증시 연쇄 폭락. 20일선 이탈 대응력"},
    {"date": "2018-12-24", "name": "미중 무역전쟁 바닥", "type": "safe", "desc": "산타 랠리 직전의 역발상 매수 타점"},
    {"date": "2020-02-24", "name": "코로나 팬데믹 폭락", "type": "danger", "desc": "TQQQ -70% 지옥 구간. VIX Spike의 위력"},
    {"date": "2020-03-23", "name": "코로나 대바닥", "type": "safe", "desc": "역사적 보라색 신호(Purple) 발생 시점"},
    {"date": "2022-01-05", "name": "금리인상 하락장 시작", "type": "danger", "desc": "1년 내내 이어진 TQQQ의 침체기 회피"}
]

# ── 데이터 로딩 ──
@st.cache_data(ttl=3600, show_spinner=False)
def load_v8_turbo_full(ticker, start_year):
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
        
    combined = df.join(vix['Close'].to_frame('VIX'), how='inner')
    combined = combined.join(ovx['Close'].to_frame('OVX'), how='left')
    combined['Spread'] = (tnx['Close'] - irx['Close'])
    
    # 지표 계산
    combined['MA20'] = combined['Close'].rolling(20).mean()
    combined['MA50'] = combined['Close'].rolling(50).mean()
    combined['MA200'] = combined['Close'].rolling(200).mean()
    combined['VIX_MA5'] = combined['VIX'].rolling(5).mean()
    
    combined['OVX'] = combined['OVX'].fillna(30)
    combined['Spread'] = combined['Spread'].fillna(1.0)
    combined.index = pd.to_datetime(combined.index).tz_localize(None)
    return combined.dropna(subset=['Close', 'VIX', 'MA200'])

# ── V8-Turbo 판정 로직 ──
def calculate_v8_turbo_signals(df):
    df = df.copy()
    W_vix, W_ovx = 1.0, 1.2

    def get_status(row):
        c, m20, m50, m200 = row['Close'], row['MA20'], row['MA50'], row['MA200']
        v, v_ma5, o, s = row['VIX'], row['VIX_MA5'], row['OVX'], row['Spread']
        
        mult = 2.5 if c < m50 else 1.0
        pen = ((W_vix * max(0, v - 24)) + (W_ovx * max(0, o - 34)) + (25 if s < -0.5 else 0)) * mult
        cms = 100 - pen
        v_spike = v / v_ma5 > 1.25 if v_ma5 > 0 else False
        
        if c < m200 and cms < 45: return '🔴무조건탈출(Red)', cms
        if c < m20 or v_spike: return '⚠️초정밀경보(Turbo)', cms
        if cms >= 55: return '🟢야수본능(Green)', cms
        if c < (m200 * 0.85): return '🔥역발상매수', cms
        return '🟡안전관망(Yellow)', cms

    res = df.apply(get_status, axis=1, result_type='expand')
    df['신호'], df['CMS'] = res[0], res[1]
    return df

# ── 수익률 및 비중 계산 ──
def calc_turbo_returns(df, start_year):
    df = df[df.index >= f"{start_year}-01-01"].copy()
    df['daily_ret'] = df['Close'].pct_change().fillna(0)

    def get_exp(sig):
        if sig == '🟢야수본능(Green)': return 1.0
        if sig == '⚠️초정밀경보(Turbo)': return 0.2
        if sig == '🟡안전관망(Yellow)': return 0.5
        if sig == '🔥역발상매수': return 0.8
        return 0.0

    df['base_exp'] = df['신호'].apply(get_exp).shift(1).fillna(0)
    # 세이프가드 (트레일링 스탑) 적용
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
t_ticker = st.selectbox("레버리지 종목", ["TQQQ", "QLD", "SOXL", "UPRO"])
s_year = st.selectbox("시작 연도", [2010, 2015, 2020])

with st.spinner("📡 초정밀 터보 레이더 가동 중..."):
    raw = load_v8_turbo_full(t_ticker, s_year)
    sig_df = calculate_v8_turbo_signals(raw)
    perf_df = calc_turbo_returns(sig_df, s_year)

# 지표 요약
f_strat, f_bah = (perf_df['cum_strat'].iloc[-1]-1)*100, (perf_df['cum_bah'].iloc[-1]-1)*100
mdd_strat = (perf_df['cum_strat']/perf_df['cum_strat'].cummax()-1).min()*100
mdd_bah = (perf_df['cum_bah']/perf_df['cum_bah'].cummax()-1).min()*100

st.markdown("#### 📊 V8-Turbo 레버리지 성과 리포트")
m1, m2, m3, m4 = st.columns(4)
m1.metric("전략 수익률", f"{f_strat:.1f}%", delta=f"{f_strat - f_bah:.1f}%p")
m2.metric("바이앤홀드", f"{f_bah:.1f}%")
m3.metric("전략 MDD", f"{mdd_strat:.1f}%", delta=f"방어력 {abs(mdd_bah)-abs(mdd_strat):.1f}%p")
m4.metric("B&H MDD", f"{mdd_bah:.1f}%")

# 차트
fig = make_subplots(rows=2, cols=1, row_heights=[0.7, 0.3], shared_xaxes=True)
fig.add_trace(go.Scatter(x=perf_df.index, y=perf_df['Close'], name='Price'), row=1, col=1)
fig.add_trace(go.Scatter(x=perf_df.index, y=perf_df['MA20'], name='MA20(초정밀)', line=dict(color='magenta', dash='dot')), row=1, col=1)
fig.add_trace(go.Scatter(x=perf_df.index, y=perf_df['MA200'], name='MA200', line=dict(color='orange', dash='dash')), row=1, col=1)
fig.add_trace(go.Scatter(x=perf_df.index, y=(perf_df['cum_strat']-1)*100, name='전략(V8-Turbo)'), row=2, col=1)
fig.add_trace(go.Scatter(x=perf_df.index, y=(perf_df['cum_bah']-1)*100, name='B&H', line=dict(dash='dot', color='gray')), row=2, col=1)
st.plotly_chart(fig, use_container_width=True)

# 🎯 역사적 위기 검증표 (복구 완료!)
st.markdown("---")
st.markdown("#### 🎯 레버리지 위기 회피 검증 (V8-Turbo 버전)")
ev_cols = st.columns(2)
for i, ev in enumerate(EVENTS):
    ev_date = pd.Timestamp(ev['date'])
    available = perf_df.index[perf_df.index >= ev_date]
    if len(available) == 0: continue
    row = perf_df.loc[available[0]]
    sig = row['신호']
    sig_color = "red" if "탈출" in sig else ("orange" if "Turbo" in sig or
