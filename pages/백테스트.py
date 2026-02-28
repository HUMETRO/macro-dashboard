import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import yfinance as yf

st.set_page_config(page_title="V8 7대 위기 풀로드", page_icon="🛡️", layout="wide")

# ── 스타일 설정 ──
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700&display=swap');
html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; }
.event-card { border-radius: 8px; padding: 12px 16px; margin-bottom: 10px; font-size: 0.82rem; border-left: 5px solid; background: white; border: 1px solid #e2e8f0; }
.win-text { color: #16a34a; font-weight: bold; }
.loss-text { color: #dc2626; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

st.title("🛡️ V8 하이브리드: 7대 위기 풀로드 리포트")
st.caption("소장님의 지시대로 닷컴버블부터 2022년까지 7대 역사적 위기 검증 로직을 모두 복구했습니다.")

# 💡 [복구완료] 7대 역사적 위기 리스트 전체
EVENTS = [
    {"date": "2000-03-24", "name": "닷컴버블 붕괴"},
    {"date": "2008-09-15", "name": "리먼 브라더스 사태"},
    {"date": "2009-03-09", "name": "금융위기 대바닥"},
    {"date": "2011-08-08", "name": "미국 신용등급 강등"},
    {"date": "2018-12-24", "name": "미중 무역전쟁 바닥"},
    {"date": "2020-02-24", "name": "코로나 팬데믹 쇼크"},
    {"date": "2022-01-05", "name": "인플레이션 하락장"}
]

# ── 1. 설정 영역 ──
ticker = st.selectbox("종목 선택", ["QQQ", "TQQQ", "SOXX", "QLD", "SPY"])
start_year = st.selectbox("시작 연도 선택", [2000, 2010, 2015, 2020])

if ticker == "TQQQ" and start_year < 2010:
    st.info("💡 TQQQ는 상장일(2010년) 이후 데이터부터 계산되며, 이전 위기는 QQQ로 확인하시는 것을 추천합니다.")

# ── 2. 데이터 로딩 (순정) ──
@st.cache_data(ttl=3600, show_spinner=False)
def load_v8_pure_data(ticker, start_year):
    fetch_start = f"{start_year - 1}-01-01"
    df = yf.download(ticker, start=fetch_start, interval='1d', progress=False)
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    df = df[['Close']].dropna()
    vix = yf.download("^VIX", start=fetch_start, progress=False)
    if isinstance(vix.columns, pd.MultiIndex): vix.columns = vix.columns.get_level_values(0)
    combined = df.join(vix['Close'].to_frame('VIX'), how='inner')
    combined['MA20'], combined['MA50'], combined['MA200'] = combined['Close'].rolling(20).mean(), combined['Close'].rolling(50).mean(), combined['Close'].rolling(200).mean()
    combined['VIX_MA5'] = combined['VIX'].rolling(5).mean()
    return combined.dropna(subset=['Close', 'VIX', 'MA200']).tz_localize(None)

# ── 3. 성과 계산 ──
def calculate_and_backtest(df, ticker, start_year):
    df = df[df.index >= f"{start_year}-01-01"].copy()
    is_lev = ticker in ["TQQQ", "QLD"]
    
    def get_status(row):
        c, m20, m50, m200, v, v5 = row['Close'], row['MA20'], row['MA50'], row['MA200'], row['VIX'], row['VIX_MA5']
        mult = 2.0 if c < m50 else 1.0
        pen = (1.0 * max(0, v - 25)) * mult
        cms, v_spike = 100 - pen, (v / v5 > 1.25 if v5 > 0 else False)
        if c < m200 and cms < 50: return '🔴철수(Red)', cms
        if is_lev and (c < m20 or v_spike): return '⚠️터보경보(Turbo)', cms
        elif not is_lev and (c < m50 or v_spike): return '🟡조기경보(Yellow)', cms
        return '🟢매수(Green)' if cms >= 55 else '🟡관망(Yellow)', cms

    res = df.apply(get_status, axis=1, result_type='expand')
    df['신호'], df['CMS'] = res[0], res[1]
    df['daily_ret'] = df['Close'].pct_change().fillna(0)
    
    def get_exp(sig):
        if sig == '🟢매수(Green)': return 1.0
        if sig == '⚠️터보경보(Turbo)': return 0.2 if is_lev else 0.4
        return 0.0
    
    df['target_exp'] = df['신호'].apply(get_exp).shift(1).fillna(0)
    current_asset, max_asset, asset_history = 1.0, 1.0, []
    
    for i in range(len(df)):
        exp, d_ret = df['target_exp'].iloc[i], df['daily_ret'].iloc[i]
        cost = 0.002 if i > 0 and exp != df['target_exp'].iloc[i-1] else 0
        current_asset *= (1 + (d_ret * exp) - (cost if exp > 0 else 0))
        if current_asset > max_asset: max_asset = current_asset
        if current_asset / max_asset - 1 < -0.08:
            current_asset *= (1 + (d_ret * 0.3))
        asset_history.append(current_asset)
        
    df['cum_strat'], df['cum_bah'] = asset_history, (1 + df['daily_ret']).cumprod()
    df['dd_strat'] = (df['cum_strat'] / df['cum_strat'].cummax() - 1) * 100
    df['dd_bah'] = (df['cum_bah'] / df['cum_bah'].cummax() - 1) * 100
    return df

# 실행
raw_data = load_v8_pure_data(ticker, start_year)
perf_df = calculate_and_backtest(raw_data, ticker, start_year)

# 📊 지표 (소장님 순서)
f_s, f_b = (perf_df['cum_strat'].iloc[-1]-1)*100, (perf_df['cum_bah'].iloc[-1]-1)*100
mdd_s, mdd_b = perf_df['dd_strat'].min(), perf_df['dd_bah'].min()
years = (perf_df.index[-1] - perf_df.index[0]).days / 365.25
cagr_s, cagr_b = ((perf_df['cum_strat'].iloc[-1])**(1/years)-1)*100, ((perf_df['cum_bah'].iloc[-1])**(1/years)-1)*100

m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("전략 수익률", f"{f_s:,.0f}%", delta=f"{f_s - f_b:,.0f}%p")
m2.metric("전략 MDD", f"{mdd_s:.1f}%", delta=f"{abs(mdd_b)-abs(mdd_s):.1f}%p 우수")
m3.metric("전략 CAGR", f"{cagr_s:.1f}%", delta=f"{cagr_s - cagr_b:.1f}%p")
m4.metric("존버 수익률", f"{f_b:,.0f}%")
m5.metric("존버 MDD", f"{mdd_b:.1f}%")

st.plotly_chart(go.Figure([go.Scatter(x=perf_df.index, y=perf_df['cum_strat'], name='V8 전략'), 
                           go.Scatter(x=perf_df.index, y=perf_df['cum_bah'], name='B&H 존버', line=dict(dash='dot'))]).update_layout(yaxis_type="log", height=500), use_container_width=True)

# 🎯 [전체 복구] 7대 역사적 위기 방어 분석
st.markdown("---")
st.markdown("#### 🎯 7대 역사적 위기 방어 분석 (신호 이후 60일 비교)")
ev_cols = st.columns(2)
for i, ev in enumerate(EVENTS):
    ev_date = pd.Timestamp(ev['date'])
    if ev_date < perf_df.index[0]: continue
    after_data = perf_df.loc[perf_df.index >= ev_date].head(60)
    if len(after_data) < 2: continue
    s_p = (after_data['cum_strat'].iloc[-1] / after_data['cum_strat'].iloc[0] - 1) * 100
    b_p = (after_data['cum_bah'].iloc[-1] / after_data['cum_bah'].iloc[0] - 1) * 100
    with ev_cols[i % 2]:
        st.markdown(f"""
        <div class="event-card">
            <b>📅 {ev['date']} | {ev['name']}</b><br>
            당시 신호: <b>{after_data['신호'].iloc[0]}</b><br>
            <div style="font-size:0.8rem;">신호 후 60일 전략: <span class="win-text">{s_p:.1f}%</span> / 존버: <span class="loss-text">{b_p:.1f}%</span></div>
            <div style="font-size:0.8rem; font-weight:bold;">🛡️ 방어 우위: {s_p - b_p:.1f}%p</div>
        </div>
        """, unsafe_allow_html=True)
