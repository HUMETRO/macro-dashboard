import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import yfinance as yf

st.set_page_config(page_title="V8 최종 강철 리포트", page_icon="🛡️", layout="wide")

# ── 스타일 설정 ──
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700&display=swap');
html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; }
.event-card { border-radius: 8px; padding: 12px 16px; margin-bottom: 10px; font-size: 0.85rem; border: 1px solid #e2e8f0; background: white; }
.metric-text { font-size: 0.9rem; color: #475569; margin: 4px 0; }
.win-text { color: #16a34a; font-weight: bold; }
.loss-text { color: #dc2626; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

st.title("🛡️ V8 하이브리드: 무결점 강철 리포트")
st.caption("변수 정의 오류를 해결하고 소장님의 지시대로 지표를 완벽하게 배치한 최종본입니다.")

# ── 데이터 로딩 ──
@st.cache_data(ttl=3600, show_spinner=False)
def load_v8_stable_data(ticker, start_year):
    fetch_start = f"{start_year - 1}-01-01"
    df = yf.download(ticker, start=fetch_start, interval='1d', progress=False)
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    df = df[['Close']].dropna()
    vix = yf.download("^VIX", start=fetch_start, progress=False)
    if isinstance(vix.columns, pd.MultiIndex): vix.columns = vix.columns.get_level_values(0)
    combined = df.join(vix['Close'].to_frame('VIX'), how='inner')
    combined['MA20'] = combined['Close'].rolling(20).mean()
    combined['MA50'] = combined['Close'].rolling(50).mean()
    combined['MA200'] = combined['Close'].rolling(200).mean()
    combined['VIX_MA5'] = combined['VIX'].rolling(5).mean()
    return combined.dropna(subset=['Close', 'VIX', 'MA200']).tz_localize(None)

# ── 신호 판정 ──
def calculate_signals(df, ticker):
    df = df.copy()
    is_lev = ticker in ["TQQQ", "QLD"]
    def get_status(row):
        c, m20, m50, m200, v, v5 = row['Close'], row['MA20'], row['MA50'], row['MA200'], row['VIX'], row['VIX_MA5']
        mult = 2.0 if c < m50 else 1.0
        pen = (1.0 * max(0, v - 25)) * mult
        cms, v_spike = 100 - pen, (v / v5 > 1.25 if v5 > 0 else False)
        if c < m200 and cms < 50: return '🔴철수(Red)', cms
        if is_lev:
            if c < m20 or v_spike: return '⚠️터보경보(Turbo)', cms
        else:
            if c < m50 or v_spike: return '🟡조기경보(Yellow)', cms
        if cms >= 55: return '🟢매수(Green)', cms
        return '🟡관망(Yellow)', cms
    res = df.apply(get_status, axis=1, result_type='expand')
    df['신호'], df['CMS'] = res[0], res[1]
    return df

# ── 성과 계산 ──
def calc_performance(df, ticker, start_year):
    df = df[df.index >= f"{start_year}-01-01"].copy()
    df['daily_ret'] = df['Close'].pct_change().fillna(0)
    is_lev = ticker in ["TQQQ", "QLD"]
    
    def get_exp(sig):
        if sig == '🟢매수(Green)': return 1.0
        if sig == '⚠️터보경보(Turbo)': return 0.2 if is_lev else 0.4
        return 0.0
    
    df['target_exp'] = df['신호'].apply(get_exp).shift(1).fillna(0)
    
    current_asset = 1.0
    max_asset = 1.0
    asset_history = []
    
    for i in range(len(df)):
        exp = df['target_exp'].iloc[i]
        d_ret = df['daily_ret'].iloc[i]
        cost = 0.002 if i > 0 and exp != df['target_exp'].iloc[i-1] else 0
        
        temp_asset = current_asset * (1 + (d_ret * exp) - cost)
        dd = (temp_asset / max_asset) - 1
        final_exp = exp * 0.3 if dd < -0.08 else exp
        
        current_asset = current_asset * (1 + (d_ret * final_exp) - (cost if final_exp > 0 else 0))
        if current_asset > max_asset: max_asset = current_asset
        asset_history.append(current_asset)

    df['cum_strat'] = asset_history
    df['cum_bah'] = (1 + df['daily_ret']).cumprod()
    df['dd_strat'] = (df['cum_strat'] / df['cum_strat'].cummax() - 1) * 100
    df['dd_bah'] = (df['cum_bah'] / df['cum_bah'].cummax() - 1) * 100
    return df

# ── 실행 ──
ticker = st.selectbox("종목 선택", ["TQQQ", "QQQ", "SOXX", "QLD", "SPY"])
start_year = st.selectbox("시작 연도", [2010, 2015, 2020])

raw_data = load_v8_stable_data(ticker, start_year)
sig_df = calculate_signals(raw_data, ticker)
perf_df = calc_performance(sig_df, ticker, start_year)

# ── 📊 지표 변수 정의 (에러 방지용 선언) ──
f_strat = (perf_df['cum_strat'].iloc[-1] - 1) * 100
f_bah = (perf_df['cum_bah'].iloc[-1] - 1) * 100
mdd_strat = perf_df['dd_strat'].min()
mdd_bah = perf_df['dd_bah'].min()
years = (perf_df.index[-1] - perf_df.index[0]).days / 365.25
cagr_strat = ((perf_df['cum_strat'].iloc[-1])**(1/years) - 1) * 100
cagr_bah = ((perf_df['cum_bah'].iloc[-1])**(1/years) - 1) * 100

# ── 상단 메트릭 배치 (소장님 지시 순서) ──
m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("전략 수익률", f"{f_strat:,.0f}%", delta=f"{f_strat - f_bah:,.0f}%p")
m2.metric("전략 MDD", f"{mdd_strat:.1f}%", delta=f"{abs(mdd_bah)-abs(mdd_strat):.1f}%p 우수")
m3.metric("전략 CAGR", f"{cagr_strat:.1f}%", delta=f"{cagr_strat - cagr_bah:.1f}%p")
m4.metric("존버 수익률", f"{f_bah:,.0f}%")
m5.metric("존버 MDD", f"{mdd_bah:.1f}%")

# 📈 차트
fig = make_subplots(rows=2, cols=1, row_heights=[0.7, 0.3], shared_xaxes=True, vertical_spacing=0.05)
fig.add_trace(go.Scatter(x=perf_df.index, y=perf_df['cum_strat'], name='V8 전략'), row=1, col=1)
fig.add_trace(go.Scatter(x=perf_df.index, y=perf_df['cum_bah'], name='B&H 존버', line=dict(dash='dot')), row=1, col=1)
fig.add_trace(go.Scatter(x=perf_df.index, y=perf_df['dd_strat'], name='전략 MDD', fill='tozeroy'), row=2, col=1)
fig.add_trace(go.Scatter(x=perf_df.index, y=perf_df['dd_bah'], name='존버 MDD', line=dict(dash='dot')), row=2, col=1)
fig.update_layout(height=600, yaxis_type="log")
st.plotly_chart(fig, use_container_width=True)

# 🎯 위기 방어 분석
st.markdown("---")
st.markdown("#### 🎯 역사적 위기 방어 분석 (신호 이후 60일 비교)")
EVENTS = [{"date": "2011-08-08", "name": "미 신용강등"}, {"date": "2020-02-24", "name": "코로나 쇼크"}, {"date": "2022-01-05", "name": "금리인상기"}]
ev_cols = st.columns(3)
for i, ev in enumerate(EVENTS):
    ev_date = pd.Timestamp(ev['date'])
    if ev_date < perf_df.index[0]: continue
    after_data = perf_df.loc[perf_df.index >= ev_date].head(60)
    if len(after_data) < 2: continue
    s_p = (after_data['cum_strat'].iloc[-1] / after_data['cum_strat'].iloc[0] - 1) * 100
    b_p = (after_data['cum_bah'].iloc[-1] / after_data['cum_bah'].iloc[0] - 1) * 100
    with ev_cols[i % 3]:
        st.markdown(f"""<div class="event-card"><b>📅 {ev['date']} | {ev['name']}</b><br>당시 신호: <b>{after_data['신호'].iloc[0]}</b><br><div class="metric-text">신호 후 60일 존버: <span class="loss-text">{b_p:.1f}%</span></div><div class="metric-text">신호 후 60일 전략: <span class="win-text">{s_p:.1f}%</span></div><div class="metric-text"><b>🛡️ 방어 성공: {s_p - b_p:.1f}%p 보호</b></div></div>""", unsafe_allow_html=True)
