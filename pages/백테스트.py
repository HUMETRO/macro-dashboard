import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import yfinance as yf

st.set_page_config(page_title="V9 Survivor 최종", page_icon="🛡️", layout="wide")

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

st.title("🛡️ V9 하이브리드: 닷컴버블 생존 엔진 (Survivor)")
st.caption("레버리지 폭락 시 자산 증발을 방지하는 로직을 탑재하여 닷컴버블의 혹독한 시련을 재검증합니다.")

# 💡 역사적 위기 리스트
EVENTS = [
    {"date": "2000-03-24", "name": "닷컴버블 붕괴", "type": "danger", "desc": "가상 TQQQ로 나스닥 -80% 대피 검증"},
    {"date": "2008-09-15", "name": "리먼 사태", "type": "danger", "desc": "금융위기 당시 생존 여부 확인"},
    {"date": "2009-03-09", "name": "금융위기 바닥", "type": "safe", "desc": "역발상 매수 타점"},
    {"date": "2011-08-08", "name": "미 신용등급 강등", "type": "danger", "desc": "유럽 재정위기 폭락 대응"},
    {"date": "2018-12-24", "name": "무역전쟁 바닥", "type": "safe", "desc": "하락 끝자락 매수 신호"},
    {"date": "2020-02-24", "name": "코로나 쇼크", "type": "danger", "desc": "VIX Spike 조기경보 작동"},
    {"date": "2022-01-05", "name": "인플레이션 하락장", "type": "danger", "desc": "긴 하락장 속 자산 방어력"}
]

@st.cache_data(ttl=3600, show_spinner=False)
def load_v9_survivor_data(ticker, start_year):
    fetch_start = f"{start_year - 1}-01-01"
    raw = yf.download(ticker, start=fetch_start, progress=False)
    if isinstance(raw.columns, pd.MultiIndex): raw.columns = raw.columns.get_level_values(0)
    
    qqq = yf.download("QQQ", start=fetch_start, progress=False)
    if isinstance(qqq.columns, pd.MultiIndex): qqq.columns = qqq.columns.get_level_values(0)
    
    lev = 3.0 if ticker == "TQQQ" else (2.0 if ticker == "QLD" else 1.0)
    combined = qqq[['Close']].rename(columns={'Close': 'QQQ_Close'})
    combined['Actual_Close'] = raw['Close']
    
    combined['QQQ_Ret'] = combined['QQQ_Close'].pct_change().fillna(0)
    combined['Actual_Ret'] = combined['Actual_Close'].pct_change()
    
    # 실제 데이터가 있으면 실제를, 없으면 가상(QQQ*배수) 수익률 사용
    combined['Final_Ret'] = combined['Actual_Ret'].fillna(combined['QQQ_Ret'] * lev).fillna(0)
    
    vix = yf.download("^VIX", start=fetch_start, progress=False)
    if isinstance(vix.columns, pd.MultiIndex): vix.columns = vix.columns.get_level_values(0)
    combined = combined.join(vix['Close'].to_frame('VIX'), how='inner')
    
    combined['MA20'] = combined['QQQ_Close'].rolling(20).mean()
    combined['MA50'] = combined['QQQ_Close'].rolling(50).mean()
    combined['MA200'] = combined['QQQ_Close'].rolling(200).mean()
    combined['VIX_MA5'] = combined['VIX'].rolling(5).mean()
    
    return combined.dropna(subset=['MA200']).tz_localize(None), lev

def calculate_v9_signals(df, lev):
    df = df.copy()
    def get_status(row):
        c, m20, m50, m200, v, v5 = row['QQQ_Close'], row['MA20'], row['MA50'], row['MA200'], row['VIX'], row['VIX_MA5']
        mult = 2.0 if c < m50 else 1.0
        pen = (1.0 * max(0, v - 25)) * mult
        cms, v_spike = 100 - pen, (v / v5 > 1.25 if v5 > 0 else False)
        
        if c < m200 and cms < 50: return '🔴철수(Red)', cms
        if lev >= 2.0:
            if c < m20 or v_spike: return '⚠️터보경보(Turbo)', cms
        else:
            if c < m50 or v_spike: return '🟡조기경보(Yellow)', cms
        if cms >= 55: return '🟢매수(Green)', cms
        return '🟡관망(Yellow)', cms
        
    res = df.apply(get_status, axis=1, result_type='expand')
    df['신호'], df['CMS'] = res[0], res[1]
    return df

def calc_performance(df, start_year, lev):
    df = df[df.index >= f"{start_year}-01-01"].copy()
    def get_exp(sig):
        if sig == '🟢매수(Green)': return 1.0
        if sig == '⚠️터보경보(Turbo)': return 0.2 if lev > 1 else 0.4
        return 0.0
    
    df['base_exp'] = df['신호'].apply(get_exp).shift(1).fillna(0)
    
    # 💡 누적 수익률 계산 시 파산 방지 로직 (수익률이 -100%가 되지 않도록 클리핑)
    # 실제 존버(B&H) 수익률
    df['bah_daily'] = df['Final_Ret'].clip(lower=-0.999) 
    df['strat_daily'] = (df['Final_Ret'] * df['base_exp'] - 0.002).clip(lower=-0.999)
    
    df['cum_strat'] = (1 + df['strat_daily']).cumprod()
    df['cum_bah'] = (1 + df['bah_daily']).cumprod()
    df['dd_strat'] = (df['cum_strat'] / df['cum_strat'].cummax() - 1) * 100
    df['dd_bah'] = (df['cum_bah'] / df['cum_bah'].cummax() - 1) * 100
    return df

# 실행부
ticker = st.selectbox("종목 선택", ["TQQQ", "QLD", "QQQ"])
start_year = st.selectbox("시작 연도", [2000, 2010, 2020])

raw_df, lev = load_v9_survivor_data(ticker, start_year)
sig_df = calculate_v9_signals(raw_df, lev)
perf_df = calc_performance(sig_df, start_year, lev)

# 📊 지표 출력
f_s, f_b = (perf_df['cum_strat'].iloc[-1]-1)*100, (perf_df['cum_bah'].iloc[-1]-1)*100
mdd_s, mdd_b = perf_df['dd_strat'].min(), perf_df['dd_bah'].min()
years = (perf_df.index[-1] - perf_df.index[0]).days / 365.25
cagr_s = ((perf_df['cum_strat'].iloc[-1])**(1/years) - 1) * 100

m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("전략 수익률", f"{f_s:,.0f}%", delta=f"{f_s-f_b:,.0f}%p")
m2.metric("전략 MDD", f"{mdd_s:.1f}%", delta=f"{abs(mdd_b)-abs(mdd_s):.1f}%p 우수")
m3.metric("전략 CAGR", f"{cagr_s:.1f}%")
m4.metric("존버 수익률", f"{f_b:,.0f}%")
m5.metric("존버 MDD", f"{mdd_b:.1f}%")

st.plotly_chart(go.Figure([go.Scatter(x=perf_df.index, y=perf_df['cum_strat'], name='V9 전략'), 
                           go.Scatter(x=perf_df.index, y=perf_df['cum_bah'], name='존버', line=dict(dash='dot'))]).update_layout(yaxis_type="log", height=500))

# 🎯 회피 검증 섹션
st.markdown("---")
st.markdown("#### 🎯 7대 역사적 위기 회피 검증 (가상 데이터 포함)")
ev_cols = st.columns(2)
for i, ev in enumerate(EVENTS):
    ev_date = pd.Timestamp(ev['date'])
    if ev_date < perf_df.index[0]: continue
    row = perf_df.loc[perf_df.index >= ev_date].iloc[0]
    sig_color = "red" if "철수" in row['신호'] else ("orange" if "경보" in row['신호'] else "green")
    with ev_cols[i % 2]:
        st.markdown(f"""<div class="event-card {'ev-safe' if ev['type']=='safe' else 'ev-danger'}">
        <b>📅 {ev['date']} | {ev['name']}</b><br>신호: <span style="color:{sig_color}; font-weight:bold;">{row['신호']}</span><br><small>{ev['desc']}</small></div>""", unsafe_allow_html=True)
