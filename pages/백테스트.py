import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import yfinance as yf

st.set_page_config(page_title="V8 하이브리드 백테스트", page_icon="🚦", layout="wide")

# ── 스타일 설정 ──
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700&display=swap');
html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; }
.v8-card { background: #f8fafc; border: 1px solid #e2e8f0; padding: 20px; border-radius: 12px; margin-bottom: 20px; }
.event-card { border-radius: 8px; padding: 12px 16px; margin-bottom: 10px; font-size: 0.9rem; border-left: 5px solid; }
.ev-safe { background:#f0fdf4; border-color:#10b981; color: #166534; }
.ev-danger { background:#fef2f2; border-color:#ef4444; color: #991b1b; }
</style>
""", unsafe_allow_html=True)

st.title("🚦 V8 하이브리드: 통합 종목 백테스트")
st.caption("지수(1배)와 레버리지(2/3배)를 모두 지원하며, 종목 특성에 맞는 최적의 알고리즘을 자동 적용합니다.")

# ── 역사적 위기 리스트 ──
EVENTS = [
    {"date": "2000-03-24", "name": "닷컴버블 붕괴", "type": "danger", "desc": "나스닥 -80% 하락의 전설적 지옥 구간"},
    {"date": "2008-09-15", "name": "리먼 브라더스 파산", "type": "danger", "desc": "금융위기 정점 및 200일선 붕괴"},
    {"date": "2020-02-24", "name": "코로나 팬데믹 쇼크", "type": "danger", "desc": "역사상 가장 빠른 VIX Spike 발생 구간"},
    {"date": "2022-01-05", "name": "인플레이션 하락장", "type": "danger", "desc": "1년 내내 이어진 금리 인상 하락장"}
]

# ── 데이터 로딩 ──
@st.cache_data(ttl=3600, show_spinner=False)
def load_hybrid_data(ticker, start_year):
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
    combined['MA20'] = combined['Close'].rolling(20).mean()
    combined['MA50'] = combined['Close'].rolling(50).mean()
    combined['MA200'] = combined['Close'].rolling(200).mean()
    combined['VIX_MA5'] = combined['VIX'].rolling(5).mean()
    
    combined['OVX'] = combined['OVX'].fillna(30)
    combined['Spread'] = combined['Spread'].fillna(1.0)
    return combined.dropna(subset=['Close', 'VIX', 'MA200']).tz_localize(None)

# ── 하이브리드 판정 로직 ──
def calculate_hybrid_signals(df, ticker):
    df = df.copy()
    is_lev = ticker in ["TQQQ", "QLD", "SOXL", "UPRO"] # 레버리지 여부 확인

    def get_status(row):
        c, m20, m50, m200 = row['Close'], row['MA20'], row['MA50'], row['MA200']
        v, v_ma5, o, s = row['VIX'], row['VIX_MA5'], row['OVX'], row['Spread']
        
        # 1. 가중치 설정 (레버리지는 더 민감하게)
        mult = 2.5 if (is_lev and c < m50) else (2.0 if c < m50 else 1.0)
        pen = ((1.0 * max(0, v - 25)) + (1.2 * max(0, o - 35)) + (20 if s < -0.5 else 0)) * mult
        cms = 100 - pen
        v_spike = v / v_ma5 > 1.25 if v_ma5 > 0 else False
        
        # 2. 판정 (레버리지는 20일선 기준, 일반은 50일선 기준)
        if c < m200 and cms < 45: return '🔴전략적철수(Red)', cms
        
        if is_lev: # 레버리지용 초정밀 레이더
            if c < m20 or v_spike: return '⚠️초정밀경보(Turbo)', cms
        else: # 일반 지수용 레이더
            if c < m50 or v_spike: return '🟡조기경보(Yellow)', cms

        if cms >= 55: return '🟢매수(Green)', cms
        if c < (m200 * 0.90): return '🔥역발상매수', cms
        return '🟡안전관망(Yellow)', cms

    res = df.apply(get_status, axis=1, result_type='expand')
    df['신호'], df['CMS'] = res[0], res[1]
    return df

# ── 수익률 계산 (비중 자동 조절) ──
def calc_hybrid_returns(df, ticker, start_year):
    df = df[df.index >= f"{start_year}-01-01"].copy()
    df['daily_ret'] = df['Close'].pct_change().fillna(0)
    is_lev = ticker in ["TQQQ", "QLD", "SOXL", "UPRO"]

    def get_exp(sig):
        if sig == '🟢매수(Green)': return 1.0
        if sig == '⚠️초정밀경보(Turbo)': return 0.2 if is_lev else 0.4
        if sig == '🟡조기경보(Yellow)': return 0.4
        if sig == '🟡안전관망(Yellow)': return 0.7
        if sig == '🔥역발상매수': return 0.8
        return 0.0

    df['base_exp'] = df['신호'].apply(get_exp).shift(1).fillna(0)
    
    # 세이프가드 (트레일링 스탑)
    final_exp, cur_cum, max_cum = [], 1.0, 1.0
    for i in range(len(df)):
        exp, d_ret = df['base_exp'].iloc[i], df['daily_ret'].iloc[i]
        cur_cum *= (1 + d_ret * exp)
        if cur_cum > max_cum: max_cum = cur_cum
        dd = (cur_cum / max_cum) - 1
        # 고점대비 -8% 시 비중 30% 축소
        actual_exp = exp * 0.3 if dd < -0.08 else exp
        final_exp.append(actual_exp)

    df['invested'] = final_exp
    df['strat_ret'] = df['daily_ret'] * df['invested']
    df['cum_strat'] = (1 + df['strat_ret']).cumprod()
    df['cum_bah'] = (1 + df['daily_ret']).cumprod()
    return df

# ── UI 및 실행 ──
ticker = st.selectbox("종목 선택", ["QQQ", "SOXX", "SPY", "TQQQ", "QLD", "SOXL"])
start_year = st.selectbox("시작 연도", [2000, 2010, 2020])

with st.spinner("📡 하이브리드 엔진 분석 중..."):
    raw = load_hybrid_data(ticker, start_year)
    sig_df = calculate_hybrid_signals(raw, ticker)
    perf_df = calc_hybrid_returns(sig_df, ticker, start_year)

# 지표 요약
f_strat, f_bah = (perf_df['cum_strat'].iloc[-1]-1)*100, (perf_df['cum_bah'].iloc[-1]-1)*100
mdd_strat = (perf_df['cum_strat']/perf_df['cum_strat'].cummax()-1).min()*100
mdd_bah = (perf_df['cum_bah']/perf_df['cum_bah'].cummax()-1).min()*100

st.markdown("#### 📊 전략 성과 요약")
m1, m2, m3, m4 = st.columns(4)
m1.metric("전략 수익률", f"{f_strat:.1f}%", delta=f"{f_strat - f_bah:.1f}%p")
m2.metric("바이앤홀드", f"{f_bah:.1f}%")
m3.metric("전략 MDD", f"{mdd_strat:.1f}%")
m4.metric("B&H MDD", f"{mdd_bah:.1f}%")

# 차트
fig = make_subplots(rows=2, cols=1, row_heights=[0.7, 0.3], shared_xaxes=True)
fig.add_trace(go.Scatter(x=perf_df.index, y=perf_df['Close'], name='Price'), row=1, col=1)
fig.add_trace(go.Scatter(x=perf_df.index, y=perf_df['MA200'], name='200일선', line=dict(dash='dash', color='orange')), row=1, col=1)
fig.add_trace(go.Scatter(x=perf_df.index, y=(perf_df['cum_strat']-1)*100, name='전략 수익률'), row=2, col=1)
fig.add_trace(go.Scatter(x=perf_df.index, y=(perf_df['cum_bah']-1)*100, name='존버 수익률', line=dict(dash='dot', color='gray')), row=2, col=1)
st.plotly_chart(fig, use_container_width=True)

# 🎯 위기 검증표 (완벽 복구!)
st.markdown("---")
st.markdown("#### 🎯 역사적 위기 회피 검증")
ev_cols = st.columns(2)
for i, ev in enumerate(EVENTS):
    ev_date = pd.Timestamp(ev['date'])
    available = perf_df.index[perf_df.index >= ev_date]
    if len(available) == 0: continue
    row = perf_df.loc[available[0]]
    sig = row['신호']
    
    with ev_cols[i % 2]:
        st.markdown(f"""
<div class="event-card {'ev-safe' if ev['type']=='safe' else 'ev-danger'}">
    <b>📅 {ev['date']} | {ev['name']}</b><br>
    신호: <b>{sig}</b> | CMS: {row['CMS']:.1f}점
</div>
""", unsafe_allow_html=True)
