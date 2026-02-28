import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import yfinance as yf

st.set_page_config(page_title="V8 조기경보 & 위기검증", page_icon="🚀", layout="wide")

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

st.title("🚀 V8 조기경보(EWS) & 역사적 위기검증")
st.caption("타이탄 알파 V8: VIX 변동 속도와 MA50 전술 필터를 결합하여 위기 대응 속도를 극대화한 최종 모델입니다.")

# ── 역사적 위기 리스트 ──
EVENTS = [
    {"date": "2000-03-24", "name": "닷컴버블 붕괴 시작", "type": "danger", "desc": "과연 조기경보가 며칠 먼저 반응했는가?"},
    {"date": "2008-09-15", "name": "리먼 브라더스 파산", "type": "danger", "desc": "금융위기 정점. MA50 페널티 가속기가 작동할 시기"},
    {"date": "2009-03-09", "name": "금융위기 대바닥", "type": "safe", "desc": "공포 속의 역발상 매수 타점 포착"},
    {"date": "2020-02-24", "name": "코로나 팬데믹 쇼크", "type": "danger", "desc": "VIX Spike 로직이 빛을 발해야 하는 구간"},
    {"date": "2020-03-23", "name": "코로나 최저점", "type": "safe", "desc": "역사적 V자 반등의 시작점"},
    {"date": "2022-01-05", "name": "인플레이션 하락장", "type": "danger", "desc": "금리 인상 본격화와 200일선 붕괴 대응"}
]

# ── 데이터 로딩 ──
@st.cache_data(ttl=3600, show_spinner=False)
def load_v8_full_data(ticker, start_year):
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
    
    # V8 데이터 계산
    combined['VIX_MA5'] = combined['VIX'].rolling(5).mean()
    combined['MA50'] = combined['Close'].rolling(50).mean()
    combined['MA200'] = combined['Close'].rolling(200).mean()
    
    combined['OVX'] = combined['OVX'].fillna(30)
    combined['Spread'] = combined['Spread'].fillna(1.0)
    combined.index = pd.to_datetime(combined.index).tz_localize(None)
    return combined.dropna(subset=['Close', 'VIX', 'MA200'])

# ── V8 조기경보 판정 로직 ──
def calculate_v8_signals(df):
    df = df.copy()
    W_vix, W_ovx = 1.0, 1.2

    def get_status(row):
        v, o, s, c, m50, m200, v_ma5 = row['VIX'], row['OVX'], row['Spread'], row['Close'], row['MA50'], row['MA200'], row['VIX_MA5']
        
        # 1. MA50 전술 필터 (가중치 2배)
        mult = 2.0 if c < m50 else 1.0
        pen = ((W_vix * max(0, v - 25)) + (W_ovx * max(0, o - 35)) + (20 if s < -0.5 else 0)) * mult
        cms = 100 - pen
        
        # 2. VIX Spike 감지 (1.25배 급등)
        vix_spike = v / v_ma5 > 1.25 if v_ma5 > 0 else False
        
        # [단계별 판정]
        if c < m200 and cms < 50: return '🔴전략적철수(Red)', cms
        if c < m50 or vix_spike: return '🟡조기경보(Yellow)', cms
        if cms >= 50: return '🟢매수(Green)', cms
        if c < (m200 * 0.90): return '🔥역발상매수', cms
        return '🟡관망(Yellow)', cms

    res = df.apply(get_status, axis=1, result_type='expand')
    df['신호'], df['CMS'] = res[0], res[1]
    return df

# ── V8 비중 및 수익률 계산 ──
def calc_returns_v8_final(df, start_year):
    df = df.copy()
    start_dt = f"{start_year}-01-01"
    df = df[df.index >= start_dt]
    df['daily_ret'] = df['Close'].pct_change().fillna(0)

    def get_v8_exp(sig):
        if sig == '🟢매수(Green)': return 1.0
        if sig == '🟡조기경보(Yellow)': return 0.4
        if sig == '🟡관망(Yellow)': return 0.7
        if sig == '🔥역발상매수': return 0.8
        return 0.0

    df['base_exp'] = df['신호'].apply(get_v8_exp).shift(1).fillna(0)
    
    final_exp, cur_cum, max_cum = [], 1.0, 1.0
    for i in range(len(df)):
        exp, d_ret = df['base_exp'].iloc[i], df['daily_ret'].iloc[i]
        cur_cum *= (1 + d_ret * exp)
        if cur_cum > max_cum: max_cum = cur_cum
        dd = (cur_cum / max_cum) - 1
        # 세이프가드 유지
        actual_exp = exp * 0.3 if dd < -0.08 else exp
        final_exp.append(actual_exp)

    df['invested'] = final_exp
    df['strat_ret'] = df['daily_ret'] * df['invested']
    df['cum_strat'] = (1 + df['strat_ret']).cumprod()
    df['cum_bah'] = (1 + df['daily_ret']).cumprod()
    return df

# ── 실행 및 출력 ──
col_top1, col_top2 = st.columns([2, 1])
with col_top1: ticker = st.selectbox("분석 종목", ["QQQ", "SPY", "SOXX"])
with col_top2: start_year = st.selectbox("시작 연도", [2000, 2010, 2020])

with st.spinner("📡 V8 엔진 분석 중..."):
    raw = load_v8_full_data(ticker, start_year)
    sig_df = calculate_v8_signals(raw)
    perf_df = calc_returns_v8_final(sig_df, start_year)

# 지표 요약
f_strat, f_bah = (perf_df['cum_strat'].iloc[-1]-1)*100, (perf_df['cum_bah'].iloc[-1]-1)*100
mdd_strat = (perf_df['cum_strat']/perf_df['cum_strat'].cummax()-1).min()*100
mdd_bah = (perf_df['cum_bah']/perf_df['cum_bah'].cummax()-1).min()*100

st.markdown("#### 📊 V8 세이프가드 성과")
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

# ── 위기 검증표 복구! ──
st.markdown("---")
st.markdown("#### 🎯 역사적 경제위기 회피 검증 (V8 조기경보 버전)")
ev_cols = st.columns(2)
for i, ev in enumerate(EVENTS):
    ev_date = pd.Timestamp(ev['date'])
    available = perf_df.index[perf_df.index >= ev_date]
    if len(available) == 0: continue
    row = perf_df.loc[available[0]]
    sig = row['신호']
    
    # 신호에 따른 색상
    sig_color = "red" if "철수" in sig else ("orange" if "조기경보" in sig or "관망" in sig else "green")
    if "역발상" in sig: sig_color = "purple"
    
    with ev_cols[i % 2]:
        st.markdown(f"""
<div class="event-card {'ev-safe' if ev['type']=='safe' else 'ev-danger'}">
    <b>📅 {ev['date']} | {ev['name']}</b><br>
    <span style="color:{sig_color}; font-weight:800; font-size:1.1rem;">당시 신호: {sig}</span><br>
    <small>CMS 점수: {row['CMS']:.1f}점 | {ev['desc']}</small>
</div>
""", unsafe_allow_html=True)
