import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime

st.set_page_config(page_title="CMS 신호 백테스트", page_icon="🚦", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700&display=swap');
html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; }
.block-container { padding-top: 3.5rem !important; }

.stat-card { background: #f8faff; border: 1px solid #dbeafe; border-radius: 10px; padding: 16px; text-align: center; margin-bottom: 10px; }
.stat-num  { font-size: 1.6rem; font-weight: 800; }
.stat-label{ font-size: 0.78rem; color: #6b7280; margin-top: 2px; }

.event-card { border-radius: 8px; padding: 10px 14px; margin-bottom: 8px; font-size: 0.84rem; line-height: 1.5; border-left: 4px solid; }
.ev-safe   { background:#f0fdf4; border-color:#10b981; }
.ev-danger { background:#fef2f2; border-color:#ef4444; }
.ev-watch  { background:#fffbeb; border-color:#f59e0b; }

/* 신호등 색상 */
.sig-green  { color: #059669; font-weight: 800; }
.sig-yellow { color: #d97706; font-weight: 800; }
.sig-red    { color: #dc2626; font-weight: 800; }
.sig-titan  { color: #7c3aed; font-weight: 800; } /* 역발상 보라색 */
</style>
""", unsafe_allow_html=True)

st.title("🚦 통합 매크로 스코어(CMS) 백테스트")
st.caption("타이탄 알파의 설계도: VIX(공포), OVX(전쟁), Spread(신용)를 통합한 신호등 퀀트 엔진입니다.")
st.markdown("---")

EVENTS = [
    {"date": "2000-03-24", "name": "닷컴버블 붕괴 시작", "type": "danger", "desc": "나스닥 고점 형성 후 200일선 붕괴. -80% 지옥의 시작"},
    {"date": "2002-10-09", "name": "닷컴버블 최저점", "type": "safe", "desc": "거품이 완전히 꺼진 후 형성된 역사적 대바닥"},
    {"date": "2008-09-15", "name": "리먼 파산 (금융위기)", "type": "danger", "desc": "글로벌 금융 시스템 마비. 🔴빨간불 지속 구간"},
    {"date": "2009-03-09", "name": "금융위기 대바닥", "type": "safe", "desc": "연준 양적완화. 🔥역발상 매수 타점 발생 구간"},
    {"date": "2015-08-24", "name": "중국 위안화 쇼크", "type": "danger", "desc": "중국발 공포로 나스닥 200일선 붕괴 및 블랙먼데이"},
    {"date": "2018-10-10", "name": "미중 무역전쟁 폭락", "type": "danger", "desc": "200일선 붕괴 후 12월까지 이어지는 끔찍한 하락장"},
    {"date": "2020-02-24", "name": "코로나 팬데믹 폭락", "type": "danger", "desc": "역사상 가장 빠른 속도로 수직 붕괴 (VIX 폭등)"},
    {"date": "2020-03-23", "name": "코로나 최저점", "type": "safe", "desc": "무제한 양적완화 발표. 역사적 V자 랠리 출발점"},
    {"date": "2022-01-05", "name": "인플레이션 & 긴축", "type": "danger", "desc": "금리차 역전 및 1년 내내 이어진 베어마켓"},
    {"date": "2025-04-02", "name": "트럼프 관세 충격", "type": "danger", "desc": "단기 발작 구간. VIX 상승에 따른 기계적 방어 테스트"}
]

@st.cache_data(ttl=3600, show_spinner=False)
def load_macro_data(ticker, start_year):
    start_dt = f"{start_year}-01-01"
    
    # 1. 메인 지수
    df = yf.download(ticker, start=start_dt, interval='1d', progress=False)
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    df = df[['Close']].rename(columns={'Close': 'Close'})
    
    # 2. VIX (공포)
    vix = yf.download("^VIX", start=start_dt, interval='1d', progress=False)
    if isinstance(vix.columns, pd.MultiIndex): vix.columns = vix.columns.get_level_values(0)
    vix = vix[['Close']].rename(columns={'Close': 'VIX'})
    
    # 3. OVX (원유 변동성 - 전쟁 리스크, 2007년부터 존재)
    ovx = yf.download("^OVX", start=start_dt, interval='1d', progress=False)
    if not ovx.empty:
        if isinstance(ovx.columns, pd.MultiIndex): ovx.columns = ovx.columns.get_level_values(0)
        ovx = ovx[['Close']].rename(columns={'Close': 'OVX'})
    else:
        ovx = pd.DataFrame(columns=['OVX'])
        
    # 4. 금리차 (10년물 - 3개월물)
    tnx = yf.download("^TNX", start=start_dt, interval='1d', progress=False)
    irx = yf.download("^IRX", start=start_dt, interval='1d', progress=False)
    if isinstance(tnx.columns, pd.MultiIndex): tnx.columns = tnx.columns.get_level_values(0)
    if isinstance(irx.columns, pd.MultiIndex): irx.columns = irx.columns.get_level_values(0)
    
    spread = (tnx[['Close']] - irx[['Close']]).rename(columns={'Close': 'Spread'})
    
    # 병합
    combined = df.join(vix, how='inner').join(ovx, how='left').join(spread, how='left')
    
    # OVX나 Spread가 없는 과거 데이터는 기본값으로 채움 (오류 방지)
    combined['OVX'] = combined['OVX'].fillna(30) # 35 이하이므로 패널티 0
    combined['Spread'] = combined['Spread'].fillna(1.0) # 양수이므로 패널티 0
    combined = combined.dropna(subset=['Close', 'VIX'])
    combined.index = pd.to_datetime(combined.index).tz_localize(None)
    
    return combined

def calculate_cms_signals(df):
    df = df.copy()
    
    # 200일 이동평균선 계산
    df['MA200'] = df['Close'].rolling(200).mean()
    
    # 가중치 설정 (타이탄 알파 설계도)
    W_vix = 1.5
    W_ovx = 2.0
    
    def get_status(row):
        vix = row['VIX']
        ovx = row['OVX']
        spread = row['Spread']
        close = row['Close']
        ma200 = row['MA200']
        
        # 1. 패널티 계산
        pen_vix = W_vix * max(0, vix - 22)
        pen_ovx = W_ovx * max(0, ovx - 35)
        # 금리차 역전(Spread < 0) 시 신용 경색으로 간주하여 강력한 20점 감점
        pen_credit = 20 if spread < 0 else 0 
        
        # 2. CMS 통합 스코어 산출
        cms = 100 - pen_vix - pen_ovx - pen_credit
        
        # 3. 신호 판정
        # [Titan's Secret] CMS가 55 미만(빨간불)인데, 주가가 200일선 대비 -8% 이상 급락한 극단적 공포 상태면?
        if cms < 55 and pd.notna(ma200) and close < (ma200 * 0.92):
            return '🔥역발상매수', cms
            
        if cms >= 85: return '🟢매수(Green)', cms
        if cms >= 55: return '🟡관망(Yellow)', cms
        return '🔴도망챠(Red)', cms

    # 적용
    results = df.apply(get_status, axis=1, result_type='expand')
    df['신호'] = results[0]
    df['CMS'] = results[1]
    
    return df.dropna()

def calc_strategy_return(df):
    df = df.copy()
    df['daily_ret'] = df['Close'].pct_change().fillna(0)
    
    # 💡 타임머신 버그 해결: "어제" 발생한 신호로 "오늘" 투자한다 (.shift(1))
    # '매수' 이거나 '역발상매수' 일 때만 시장에 참여 (1)
    df['invested'] = df['신호'].isin(['🟢매수(Green)', '🔥역발상매수']).shift(1).fillna(0).astype(int)
    
    df['strat_ret'] = df['daily_ret'] * df['invested']
    df['cum_bah'] = (1 + df['daily_ret']).cumprod()
    df['cum_strat'] = (1 + df['strat_ret']).cumprod()
    return df

col_opt1, col_opt2 = st.columns([2, 1])
with col_opt1:
    ticker_map = {'NASDAQ (QQQ)': 'QQQ', 'S&P500 (SPY)': 'SPY', '반도체 (SOXX)': 'SOXX'}
    selected_name = st.selectbox("분석 종목 (3대 지수)", list(ticker_map.keys()))
    ticker = ticker_map[selected_name]
with col_opt2:
    start_year = st.selectbox("시작 연도", [2000, 2005, 2008, 2010, 2015, 2020], index=0)

with st.spinner("📡 CMS 신호등 엔진 백테스트 구동 중... (데이터 수집에 약간의 시간이 소요됩니다)"):
    raw_df = load_macro_data(ticker, start_year)

if raw_df.empty or len(raw_df) < 300:
    st.error("데이터가 부족합니다.")
    st.stop()

sig_df  = calculate_cms_signals(raw_df)
perf_df = calc_strategy_return(sig_df)

final_bah   = round((perf_df['cum_bah'].iloc[-1]   - 1) * 100, 1)
final_strat = round((perf_df['cum_strat'].iloc[-1] - 1) * 100, 1)
mdd_bah     = round(((perf_df['cum_bah']   / perf_df['cum_bah'].cummax()   - 1).min()) * 100, 1)
mdd_strat   = round(((perf_df['cum_strat'] / perf_df['cum_strat'].cummax() - 1).min()) * 100, 1)

st.markdown("#### 📊 CMS 가중치 전략 성과 요약 (타임머신 오류 100% 제거)")
m1, m2, m3, m4 = st.columns(4)
m1.metric("신호전략 수익률", f"{final_strat:+.1f}%")
m2.metric("바이앤홀드 수익률", f"{final_bah:+.1f}%")
m3.metric("전략 최대낙폭(MDD)", f"{mdd_strat:.1f}%")
m4.metric("B&H 최대낙폭(MDD)", f"{mdd_bah:.1f}%")
st.markdown("---")

st.markdown("#### 📈 가격 차트 + 신호등 배경")
fig = make_subplots(rows=2, cols=1, row_heights=[0.72, 0.28], shared_xaxes=True, vertical_spacing=0.04)

sig_color_map = {
    '🟢매수(Green)': 'rgba(16,185,129,0.15)', 
    '🟡관망(Yellow)': 'rgba(245,158,11,0.15)', 
    '🔴도망챠(Red)': 'rgba(239,68,68,0.2)',
    '🔥역발상매수': 'rgba(124,58,237,0.3)' # 보라색 포인트
}
dates = sig_df.index.tolist()
sigs  = sig_df['신호'].tolist()

block_start, block_sig = dates[0], sigs[0]
for i in range(1, len(dates)):
    if sigs[i] != block_sig or i == len(dates) - 1:
        fig.add_vrect(x0=block_start, x1=dates[i], fillcolor=sig_color_map[block_sig], layer="below", line_width=0, row=1, col=1)
        block_start, block_sig = dates[i], sigs[i]

fig.add_trace(go.Scatter(x=sig_df.index, y=sig_df['Close'], name=ticker, line=dict(color='#1d4ed8', width=1.8)), row=1, col=1)

# 200일선 차트에 추가
fig.add_trace(go.Scatter(x=sig_df.index, y=sig_df['MA200'], name='200일선', line=dict(color='#047857', width=1.5, dash='dash')), row=1, col=1)

for ev in EVENTS:
    ev_date = pd.Timestamp(ev['date'])
    if ev_date < sig_df.index[0] or ev_date > sig_df.index[-1]: continue
    color = '#dc2626' if ev['type'] == 'danger' else '#059669'
    fig.add_vline(x=ev_date, line_dash="dot", line_color=color, line_width=1.5, row=1, col=1)
    fig.add_annotation(x=ev_date, y=1.02, xref='x', yref='paper', text=ev['name'][:6], showarrow=False, font=dict(size=9, color=color), textangle=-60, xanchor='left')

fig.add_trace(go.Scatter(x=perf_df.index, y=(perf_df['cum_strat'] - 1) * 100, name='CMS 신호전략', line=dict(color='#2563eb', width=2)), row=2, col=1)
fig.add_trace(go.Scatter(x=perf_df.index, y=(perf_df['cum_bah'] - 1) * 100, name='바이앤홀드', line=dict(color='#9ca3af', width=1.5, dash='dash')), row=2, col=1)
fig.add_hline(y=0, line_dash='dot', line_color='#d1d5db', row=2, col=1)

fig.update_layout(height=650, template='plotly_white', hovermode='x unified', margin=dict(l=10, r=10, t=60, b=10))
st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

st.markdown("#### 🎯 주요 역사적 이벤트 CMS 신호 검증")
ev_cols = st.columns(2)
for i, ev in enumerate(EVENTS):
    ev_date = pd.Timestamp(ev['date'])
    available = sig_df.index[sig_df.index >= ev_date]
    if len(available) == 0: continue
    closest = available[0]
    row = sig_df.loc[closest]
    sig = row['신호']
    cms_score = row['CMS']

    if '매수(Green)' in sig: sig_class = 'sig-green'
    elif '관망' in sig: sig_class = 'sig-yellow'
    elif '역발상' in sig: sig_class = 'sig-titan'
    else: sig_class = 'sig-red'
    
    ev_class  = 'ev-safe' if ev['type'] == 'safe' else 'ev-danger'

    fut_30 = sig_df.index[sig_df.index >= closest + pd.Timedelta(days=30)]
    ret_30 = f"{((sig_df.loc[fut_30[0],'Close'] / row['Close'] - 1)*100):.1f}%" if len(fut_30) else "N/A"

    verdict = ""
    if ev['type'] == 'danger' and ('도망챠' in sig or '관망' in sig): verdict = "✅ 위기 회피 성공 (방어벽 가동)"
    elif ev['type'] == 'danger' and '매수' in sig: verdict = "❌ 위기 미감지"
    elif ev['type'] == 'safe'   and ('매수' in sig or '역발상' in sig): verdict = "✅ 상승/역발상 탑승 성공"
    else: verdict = "⚠️ 보수적 관망 유지"

    with ev_cols[i % 2]:
        st.markdown(f"""
<div class="event-card {ev_class}">
    <div style="font-weight:700; margin-bottom:4px;">📅 {ev['date']} &nbsp;|&nbsp; {ev['name']}</div>
    <div>CMS 통합점수: <b>{cms_score:.1f}점</b></div>
    <div>신호: <span class="{sig_class}">{sig}</span> &nbsp;|&nbsp; 1개월 후 수익: <b>{ret_30}</b></div>
    <div style="margin-top:5px; font-weight:600;">{verdict}</div>
</div>
""", unsafe_allow_html=True)
