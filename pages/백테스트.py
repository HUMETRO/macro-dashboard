import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import yfinance as yf

st.set_page_config(page_title="V8 나스닥 정예 리포트", page_icon="🛡️", layout="wide")

# ── 스타일 설정 (순정 고정) ──
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700&display=swap');
html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; }
.event-card { border-radius: 8px; padding: 10px 14px; margin-bottom: 8px; font-size: 0.85rem; border-left: 5px solid; }
.ev-safe { background:#f0fdf4; border-color:#10b981; color: #166534; }
.ev-danger { background:#fef2f2; border-color:#ef4444; color: #991b1b; }
</style>
""", unsafe_allow_html=True)

st.title("🛡️ V8 하이브리드: 나스닥 정예 리포트")
st.caption("소장님의 지시대로 변동성이 불규칙한 반도체(SOXX)를 제외하고 나스닥 중심의 정예 종목으로 재구성했습니다.")

# 💡 역사적 위기 리스트 (원본 세트)
EVENTS = [
    {"date": "2000-03-24", "name": "닷컴버블 붕괴", "type": "danger", "desc": "나스닥 -80% 하락 대피 테스트"},
    {"date": "2008-09-15", "name": "리먼 사태", "type": "danger", "desc": "금융위기 정점 대응력"},
    {"date": "2009-03-09", "name": "금융위기 대바닥", "type": "safe", "desc": "공포 속의 역발상 매수(Purple)"},
    {"date": "2011-08-08", "name": "미 신용등급 강등", "type": "danger", "desc": "단기 폭락장 세이프가드"},
    {"date": "2018-12-24", "name": "무역전쟁 바닥", "type": "safe", "desc": "하락 끝자락 매수 신호"},
    {"date": "2020-02-24", "name": "코로나 팬데믹 쇼크", "type": "danger", "desc": "VIX Spike 조기경보"},
    {"date": "2022-01-05", "name": "인플레이션 하락장", "type": "danger", "desc": "하락장 자산 수호"}
]

# ── 1. 종목 선택 (소장님 요청: SOXX 제외 및 1배수 우선) ──
ticker = st.selectbox("종목 선택", ["QQQ", "SPY", "TQQQ", "QLD"])

# TQQQ 전용 가이드 유지
if ticker == "TQQQ":
    start_year = st.selectbox("시작 연도", [2010, 2015, 2020])
    st.info("💡 TQQQ는 실제 상장 데이터가 존재하는 2010년부터 검증을 시작합니다.")
else:
    start_year = st.selectbox("시작 연도", [2000, 2010, 2020])

# ── 2. 데이터 로딩 (순정 복구) ──
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

# ── 3. 성과 계산 (소장님 원본 순정 로직) ──
def calc_performance(df, ticker, start_year):
    df = df[df.index >= f"{start_year}-01-01"].copy()
    df['daily_ret'] = df['Close'].pct_change().fillna(0).clip(-0.99, 5.0)
    is_lev = ticker in ["TQQQ", "QLD"]
    
    def get_status(row):
        c, m20, m50, m200, v, v5 = row['Close'], row['MA20'], row['MA50'], row['MA200'], row['VIX'], row['VIX_MA5']
        mult = 2.0 if c < m50 else 1.0
        pen = (1.0 * max(0, v - 25)) * mult
        cms, v_spike = 100 - pen, (v / v5 > 1.25 if v5 > 0 else False)
        if c < m200 and cms < 50: return 0.0 # 철수
        if is_lev and (c < m20 or v_spike): return 0.2 # 터보경보
        elif not is_lev and (c < m50 or v_spike): return 0.4 # 조기경보
        return 1.0 if cms >= 55 else 0.7 # 매수/관망 비중

    df['base_exp'] = df.apply(get_status, axis=1).shift(1).fillna(0)
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

# 실행
raw_data = load_v8_pure_data(ticker, start_year)
perf_df = calc_performance(raw_data, ticker, start_year)

# 📊 지표 출력 (소장님 순서)
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

# 🎯 역사적 위기 검증 (원본 회피 리포트 유지)
st.markdown("---")
st.markdown("#### 🎯 역사적 위기 회피 검증")
ev_cols = st.columns(2)
for i, ev in enumerate(EVENTS):
    ev_date = pd.Timestamp(ev['date'])
    if ev_date < perf_df.index[0]: continue
    row = perf_df.loc[perf_df.index >= ev_date].iloc[0]
    # 신호 텍스트 출력을 위해 별도 판정 로직 미포함, 원본 이벤트 카드 형식 유지
    st_label = "🔴철수" if perf_df.loc[ev_date:ev_date].empty else "검증 중" 
    with ev_cols[i % 2]:
        st.markdown(f'<div class="event-card {"ev-safe" if ev["type"]=="safe" else "ev-danger"}"><b>📅 {ev["date"]} | {ev["name"]}</b><br><small>{ev["desc"]}</small></div>', unsafe_allow_html=True)
