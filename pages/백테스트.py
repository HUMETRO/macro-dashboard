import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import yfinance as yf

st.set_page_config(page_title="V8 최종 커스텀 리포트", page_icon="🛡️", layout="wide")

# ── 스타일 설정 ──
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700&display=swap');
html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; }
.event-card { border-radius: 8px; padding: 10px 14px; margin-bottom: 8px; font-size: 0.85rem; border-left: 5px solid; }
.ev-safe { background:#f0fdf4; border-color:#10b981; color: #166534; }
.ev-danger { background:#fef2f2; border-color:#ef4444; color: #991b1b; }
</style>
""", unsafe_allow_html=True)

st.title("🛡️ V8 하이브리드: 소장님 전용 정밀 리포트")
st.caption("소장님의 지시대로 전략의 핵심 3대 지표를 우선 배치하여 실전 대응력을 극대화했습니다.")

# ── 데이터 로딩 (Pure Close) ──
@st.cache_data(ttl=3600, show_spinner=False)
def load_v8_custom_data(ticker, start_year):
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
    return combined.dropna(subset=['Close', 'VIX', 'MA200']).tz_localize(None)

# ── 로직 및 성과 계산 (이전 안정 로직 유지) ──
def calculate_signals(df, ticker):
    df = df.copy()
    is_lev = ticker in ["TQQQ", "QLD"]
    def get_status(row):
        c, m20, m50, m200, v, v5, o, s = row['Close'], row['MA20'], row['MA50'], row['MA200'], row['VIX'], row['VIX_MA5'], row['OVX'], row['Spread']
        mult = 2.0 if c < m50 else 1.0
        pen = ((1.0 * max(0, v - 25)) + (1.2 * max(0, o - 35)) + (20 if s < -0.5 else 0)) * mult
        cms = 100 - pen
        v_spike = v / v5 > 1.25 if v5 > 0 else False
        if c < m200 and cms < 50: return '🔴철수(Red)', cms
        if is_lev:
            if c < m20 or v_spike: return '⚠️터보경보(Turbo)', cms
        else:
            if c < m50 or v_spike: return '🟡조기경보(Yellow)', cms
        if cms >= 55: return '🟢매수(Green)', cms
        if c < (m200 * 0.90): return '🔥역발상매수', cms
        return '🟡관망(Yellow)', cms
    res = df.apply(get_status, axis=1, result_type='expand')
    df['신호'], df['CMS'] = res[0], res[1]
    return df

def calc_performance(df, ticker, start_year):
    df = df[df.index >= f"{start_year}-01-01"].copy()
    df['daily_ret'] = df['Close'].pct_change().fillna(0).clip(-0.99, 5.0)
    is_lev = ticker in ["TQQQ", "QLD"]
    def get_exp(sig):
        if sig == '🟢매수(Green)': return 1.0
        if sig == '⚠️터보경보(Turbo)': return 0.2 if is_lev else 0.4
        if sig == '🟡조기경보(Yellow)': return 0.4
        if sig == '🟡관망(Yellow)': return 0.7
        if sig == '🔥역발상매수': return 0.8
        return 0.0
    df['base_exp'] = df['신호'].apply(get_exp).shift(1).fillna(0)
    final_exp, cur_cum, max_cum = [], 1.0, 1.0
    for i in range(len(df)):
        exp, d_ret = df['base_exp'].iloc[i], df['daily_ret'].iloc[i]
        cost = 0.002 if i > 0 and exp != df['base_exp'].iloc[i-1] else 0
        temp_cum = cur_cum * (1 + (d_ret * exp) - cost)
        dd = (temp_cum / max_cum) - 1
        actual_exp = exp * 0.3 if dd < -0.08 else exp
        cur_cum *= (1 + (d_ret * actual_exp) - (cost if actual_exp > 0 else 0))
        if cur_cum > max_cum: max_cum = cur_cum
        final_exp.append(actual_exp)
    df['cum_strat'] = (1 + (df['daily_ret'] * pd.Series(final_exp, index=df.index))).cumprod()
    df['cum_bah'] = (1 + df['daily_ret']).cumprod()
    df['dd_strat'] = (df['cum_strat'] / df['cum_strat'].cummax() - 1) * 100
    df['dd_bah'] = (df['cum_bah'] / df['cum_bah'].cummax() - 1) * 100
    return df

# ── 메인 실행 ──
ticker = st.selectbox("종목 선택", ["TQQQ", "QQQ", "SOXX", "QLD", "SPY"])
start_year = st.selectbox("시작 연도", [2000, 2010, 2020])

raw_data = load_v8_custom_data(ticker, start_year)
sig_df = calculate_signals(raw_data, ticker)
perf_df = calc_performance(sig_df, ticker, start_year)

# ── 📊 [소장님 지시 사항] 상단 지표 순서 재배치 ──
f_strat, f_bah = (perf_df['cum_strat'].iloc[-1]-1)*100, (perf_df['cum_bah'].iloc[-1]-1)*100
mdd_s, mdd_b = perf_df['dd_strat'].min(), perf_df['dd_bah'].min()
days = (perf_df.index[-1] - perf_df.index[0]).days
years = days / 365.25
cagr_s = ((perf_df['cum_strat'].iloc[-1])**(1/years) - 1) * 100
cagr_b = ((perf_df['cum_bah'].iloc[-1])**(1/years) - 1) * 100

# 5열 배치: 전략수익률, 전략MDD, 전략CAGR, 존버수익률, 존버MDD
m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("전략 수익률", f"{f_strat:,.0f}%", delta=f"{f_strat - f_bah:,.0f}%p")
m2.metric("전략 MDD", f"{mdd_s:.1f}%", delta=f"{abs(mdd_b)-abs(mdd_s):.1f}%p 우수")
m3.metric("전략 CAGR", f"{cagr_s:.1f}%", delta=f"{cagr_s - cagr_b:.1f}%p")
m4.metric("존버 수익률", f"{f_bah:,.0f}%")
m5.metric("존버 MDD", f"{mdd_b:.1f}%")

# 📈 [시각화] 로그 차트 및 MDD 영역

fig = make_subplots(rows=2, cols=1, row_heights=[0.7, 0.3], shared_xaxes=True, vertical_spacing=0.05)
fig.add_trace(go.Scatter(x=perf_df.index, y=perf_df['cum_strat'], name='V8 전략'), row=1, col=1)
fig.add_trace(go.Scatter(x=perf_df.index, y=perf_df['cum_bah'], name='B&H 존버', line=dict(dash='dot')), row=1, col=1)
fig.add_trace(go.Scatter(x=perf_df.index, y=perf_df['dd_strat'], name='전략 MDD', fill='tozeroy'), row=2, col=1)
fig.add_trace(go.Scatter(x=perf_df.index, y=perf_df['dd_bah'], name='존버 MDD', line=dict(dash='dot')), row=2, col=1)
fig.update_layout(height=600, yaxis_type="log")
st.plotly_chart(fig, use_container_width=True)
