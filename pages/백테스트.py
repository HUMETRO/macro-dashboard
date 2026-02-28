import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import yfinance as yf

st.set_page_config(page_title="V9 가상 TQQQ 리포트", page_icon="🏛️", layout="wide")

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

st.title("🏛️ V9-Synthetic: 닷컴버블 정밀 검증 리포트")
st.caption("2010년 이전 데이터는 QQQ를 이용해 가상 TQQQ를 생성하여 닷컴버블 대피력을 검증합니다.")

# 💡 역사적 위기 리스트
EVENTS = [
    {"date": "2000-03-24", "name": "닷컴버블 붕괴", "type": "danger", "desc": "가상 TQQQ로 나스닥 -80% 대피 검증"},
    {"date": "2008-09-15", "name": "리먼 브라더스 파산", "type": "danger", "desc": "금융위기 당시 생존 여부 확인"},
    {"date": "2020-02-24", "name": "코로나 팬데믹 쇼크", "type": "danger", "desc": "VIX Spike 조기경보 작동"},
    {"date": "2022-01-05", "name": "인플레이션 하락장", "type": "danger", "desc": "긴 하락장 속 자산 방어력"}
]

@st.cache_data(ttl=3600, show_spinner=False)
def load_synthetic_data(ticker, start_year):
    fetch_start = f"{start_year - 1}-01-01"
    # TQQQ가 없던 시절을 위해 QQQ 데이터를 기준으로 함
    base_ticker = "QQQ" if ticker in ["TQQQ", "QLD"] else ticker
    df = yf.download(base_ticker, start=fetch_start, progress=False)
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    
    # 레버리지 배수 설정
    lev_factor = 3.0 if ticker == "TQQQ" else (2.0 if ticker == "QLD" else 1.0)
    
    # 보조 지표용 QQQ (신호 판단용은 항상 지수 기준)
    df['Close_Base'] = df['Close']
    df['Daily_Ret_Base'] = df['Close'].pct_change()
    
    # 지표 계산
    vix = yf.download("^VIX", start=fetch_start, progress=False)
    for d in [vix]:
        if isinstance(d.columns, pd.MultiIndex): d.columns = d.columns.get_level_values(0)
        
    df = df.join(vix['Close'].to_frame('VIX'), how='inner')
    df['MA20'] = df['Close_Base'].rolling(20).mean()
    df['MA50'] = df['Close_Base'].rolling(50).mean()
    df['MA200'] = df['Close_Base'].rolling(200).mean()
    df['VIX_MA5'] = df['VIX'].rolling(5).mean()
    
    return df.dropna(subset=['MA200']).tz_localize(None), lev_factor

def calculate_v9_signals(df, lev_factor):
    df = df.copy()
    def get_status(row):
        c, m20, m50, m200, v, v5 = row['Close_Base'], row['MA20'], row['MA50'], row['MA200'], row['VIX'], row['VIX_MA5']
        pen = (1.0 * max(0, v - 25)) * (2.0 if c < m50 else 1.0)
        cms, v_spike = 100 - pen, (v / v5 > 1.25 if v5 > 0 else False)
        
        if c < m200 and cms < 50: return '🔴철수(Red)', cms
        if lev_factor >= 2.0:
            if c < m20 or v_spike: return '⚠️터보경보(Turbo)', cms
        else:
            if c < m50 or v_spike: return '🟡조기경보(Yellow)', cms
        if cms >= 55: return '🟢매수(Green)', cms
        return '🟡관망(Yellow)', cms
        
    res = df.apply(get_status, axis=1, result_type='expand')
    df['신호'], df['CMS'] = res[0], res[1]
    return df

def calc_performance(df, start_year, lev_factor):
    df = df[df.index >= f"{start_year}-01-01"].copy()
    
    def get_exp(sig):
        if sig == '🟢매수(Green)': return 1.0
        if sig == '⚠️터보경보(Turbo)': return 0.2 if lev_factor > 1 else 0.4
        return 0.0
        
    df['base_exp'] = df['신호'].apply(get_exp).shift(1).fillna(0)
    
    # 가상 레버리지 수익률 계산 (QQQ 수익률 * 배수)
    df['strat_ret'] = df['Daily_Ret_Base'] * df['base_exp'] * lev_factor
    df['bah_ret'] = df['Daily_Ret_Base'] * lev_factor
    
    df['cum_strat'] = (1 + df['strat_ret']).cumprod()
    df['cum_bah'] = (1 + df['bah_ret']).cumprod()
    df['dd_strat'] = (df['cum_strat'] / df['cum_strat'].cummax() - 1) * 100
    df['dd_bah'] = (df['cum_bah'] / df['cum_bah'].cummax() - 1) * 100
    return df

# 실행
ticker = st.selectbox("종목 선택", ["TQQQ", "QLD", "QQQ"])
start_year = st.selectbox("시작 연도", [2000, 2010, 2020])

raw_df, lev = load_synthetic_data(ticker, start_year)
sig_df = calculate_v9_signals(raw_df, lev)
perf_df = calc_performance(sig_df, start_year, lev)

# 📊 지표 출력 (소장님 지시 순서)
f_s, f_b = (perf_df['cum_strat'].iloc[-1]-1)*100, (perf_df['cum_bah'].iloc[-1]-1)*100
mdd_s, mdd_b = perf_df['dd_strat'].min(), perf_df['dd_bah'].min()
cagr_s = ((perf_df['cum_strat'].iloc[-1])**(365.25/(perf_df.index[-1]-perf_df.index[0]).days) - 1) * 100

m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("전략 수익률", f"{f_s:,.0f}%", delta=f"{f_s-f_b:,.0f}%p")
m2.metric("전략 MDD", f"{mdd_s:.1f}%", delta=f"{abs(mdd_b)-abs(mdd_s):.1f}%p 우수")
m3.metric("전략 CAGR", f"{cagr_s:.1f}%")
m4.metric("존버 수익률", f"{f_b:,.0f}%")
m5.metric("존버 MDD", f"{mdd_b:.1f}%")

st.plotly_chart(go.Figure([go.Scatter(x=perf_df.index, y=perf_df['cum_strat'], name='V9 가상전략'), 
                           go.Scatter(x=perf_df.index, y=perf_df['cum_bah'], name='가상 존버', line=dict(dash='dot'))]).update_layout(yaxis_type="log", height=500))

# 🎯 회피 검증 섹션 복구
st.markdown("---")
st.markdown("#### 🎯 닷컴버블 포함 역사적 위기 회피 검증")
ev_cols = st.columns(2)
for i, ev in enumerate(EVENTS):
    ev_date = pd.Timestamp(ev['date'])
    if ev_date < perf_df.index[0]: continue
    row = perf_df.loc[perf_df.index >= ev_date].iloc[0]
    with ev_cols[i % 2]:
        st.markdown(f"""<div class="event-card {'ev-safe' if ev['type']=='safe' else 'ev-danger'}">
        <b>📅 {ev['date']} | {ev['name']}</b><br>신호: <b>{row['신호']}</b><br><small>{ev['desc']}</small></div>""", unsafe_allow_html=True)
