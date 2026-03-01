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

st.title("🛡️ V8 하이브리드: 정밀 리포트")
st.caption("7대 역사적 위기 검증 시스템을 통해 전략을 백테스트합니다.")

st.markdown("""
<style>
/* ── 백테스트 스토리 카드 (흰색 글씨 영구 퇴출) ── */
.bt-card { 
    background: #f8fafc; 
    border: 1px solid #cbd5e1; 
    border-radius: 8px; 
    padding: 14px; 
    margin-bottom: 12px; 
    color: #0f172a; 
}
.bt-title { 
    font-weight: 800; 
    color: #1e293b; 
    margin-bottom: 6px; 
    font-size: 1.05rem; 
    border-bottom: 2px solid #e2e8f0;
    padding-bottom: 4px;
}
.bt-text { font-size: 0.9rem; line-height: 1.6; color: #334155; }
.bt-highlight { font-weight: 800; color: #b91c1c; } /* 하락 강조: 진한 피색 */
.bt-buy { font-weight: 800; color: #047857; } /* 방어/수익 강조: 진한 쑥색 */
</style>
""", unsafe_allow_html=True)

# 💡 역사적 위기 리스트 정의
EVENTS = [
    {"date": "2000-03-24", "name": "닷컴버블 붕괴", "type": "danger", "desc": "나스닥 -80% 하락 대피 테스트"},
    {"date": "2008-09-15", "name": "리먼 브라더스 파산", "type": "danger", "desc": "금융위기 정점 대응력"},
    {"date": "2009-03-09", "name": "금융위기 대바닥", "type": "safe", "desc": "공포 속의 역발상 매수(Purple)"},
    {"date": "2011-08-08", "name": "미국 신용등급 강등", "type": "danger", "desc": "단기 폭락장 세이프가드 작동"},
    {"date": "2018-12-24", "name": "미중 무역전쟁 바닥", "type": "safe", "desc": "하락 추세 끝자락 매수 신호"},
    {"date": "2020-02-24", "name": "코로나 팬데믹 쇼크", "type": "danger", "desc": "VIX Spike 조기경보의 핵심"},
    {"date": "2022-01-05", "name": "인플레이션 하락장", "type": "danger", "desc": "1년 내내 이어진 금리인상기 회피"}
]

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

# ── 로직 및 성과 계산 ──
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

# ── 메인 실행 (종목 순서 변경 및 SOXX 삭제 완료) ──
ticker = st.selectbox("종목 선택", ["QQQ", "SPY", "TQQQ", "QLD"])
start_year = st.selectbox("시작 연도", [2000, 2010, 2020])

raw_data = load_v8_custom_data(ticker, start_year)
sig_df = calculate_signals(raw_data, ticker)
perf_df = calc_performance(sig_df, ticker, start_year)

# ── 📊 상단 지표 순서 재배치 ──
f_strat, f_bah = (perf_df['cum_strat'].iloc[-1]-1)*100, (perf_df['cum_bah'].iloc[-1]-1)*100
mdd_s, mdd_b = perf_df['dd_strat'].min(), perf_df['dd_bah'].min()
days = (perf_df.index[-1] - perf_df.index[0]).days
years = days / 365.25
cagr_s = ((perf_df['cum_strat'].iloc[-1])**(1/years) - 1) * 100
cagr_b = ((perf_df['cum_bah'].iloc[-1])**(1/years) - 1) * 100

m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("전략 수익률", f"{f_strat:,.0f}%", delta=f"{f_strat - f_bah:,.0f}%p")
m2.metric("전략 MDD", f"{mdd_s:.1f}%", delta=f"{abs(mdd_b)-abs(mdd_s):.1f}%p 우수")
m3.metric("전략 CAGR", f"{cagr_s:.1f}%", delta=f"{cagr_s - cagr_b:.1f}%p")
m4.metric("존버 수익률", f"{f_bah:,.0f}%")
m5.metric("존버 MDD", f"{mdd_b:.1f}%")

# 📈 [시각화] 차트 영역
fig = make_subplots(rows=2, cols=1, row_heights=[0.7, 0.3], shared_xaxes=True, vertical_spacing=0.05)
fig.add_trace(go.Scatter(x=perf_df.index, y=perf_df['cum_strat'], name='V8 전략'), row=1, col=1)
fig.add_trace(go.Scatter(x=perf_df.index, y=perf_df['cum_bah'], name='B&H 존버', line=dict(dash='dot')), row=1, col=1)
fig.add_trace(go.Scatter(x=perf_df.index, y=perf_df['dd_strat'], name='전략 MDD', fill='tozeroy'), row=2, col=1)
fig.add_trace(go.Scatter(x=perf_df.index, y=perf_df['dd_bah'], name='존버 MDD', line=dict(dash='dot')), row=2, col=1)
fig.update_layout(height=600, yaxis_type="log")
st.plotly_chart(fig, use_container_width=True)

# 🎯 [복구완료] 7대 역사적 위기 회피 검증
st.markdown("---")
st.markdown("#### 🎯 7대 역사적 위기 회피 검증")
ev_cols = st.columns(2)
for i, ev in enumerate(EVENTS):
    ev_date = pd.Timestamp(ev['date'])
    if ev_date < perf_df.index[0]: continue
    
    # 해당 날짜 혹은 가장 가까운 미래 날짜의 데이터 추출
    future_data = perf_df.loc[perf_df.index >= ev_date]
    if future_data.empty: continue
    row = future_data.iloc[0]
    
    sig_color = "red" if "철수" in row['신호'] else ("orange" if "경보" in row['신호'] or "관망" in row['신호'] else "green")
    if "역발상" in row['신호']: sig_color = "purple"
    
    with ev_cols[i % 2]:
        st.markdown(f"""
<div class="event-card {'ev-safe' if ev['type']=='safe' else 'ev-danger'}">
    <b>📅 {ev['date']} | {ev['name']}</b><br>
    신호: <span style="color:{sig_color}; font-weight:800;">{row['신호']}</span><br>
    <small>CMS 점수: {row['CMS']:.1f}점 | {ev['desc']}</small>
</div>
""", unsafe_allow_html=True)
