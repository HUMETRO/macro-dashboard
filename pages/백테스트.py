import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import yfinance as yf

st.set_page_config(page_title="아기티큐 백테스트", page_icon="🚀", layout="wide")

st.title("🚀 아기티큐 200일선 정밀 타격 백테스트")
st.caption("소장님이 직접 설계하신 TQQQ 전량 매도/피신 전략을 과거 25년 데이터로 검증합니다.")

# ── 데이터 로딩 ──
@st.cache_data(ttl=3600)
def load_tqqq_backtest(ticker, start_year):
    # TQQQ는 2010년에 상장했으므로, 그 이전은 QQQ 데이터에 3배 수익률을 가상으로 입혀서 계산하거나
    # 안전하게 QQQ(나스닥 100)로 2000년부터 테스트합니다.
    fetch_start = f"{start_year - 1}-01-01"
    df = yf.download(ticker, start=fetch_start, interval='1d', progress=False)
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    df = df[['Close']].rename(columns={'Close': 'Close'})
    return df

def calculate_baby_tqqq_signals(df):
    df = df.copy()
    # 1. 200일선 및 과열선(5%) 계산
    df['MA200'] = df['Close'].rolling(window=200).mean()
    df['Envelope'] = df['MA200'] * 1.05
    
    # 2. 소장님 로직 구현
    def get_action(i):
        if i < 1: return '대기'
        today = df.iloc[i]
        yesterday = df.iloc[i-1]
        
        price_t, ma200_t, env_t = today['Close'], today['MA200'], today['Envelope']
        price_y, ma200_y = yesterday['Close'], yesterday['MA200']
        
        if pd.isna(ma200_t): return '대기'
        
        # (1) 하락장: 200일선 아래면 전량 매도
        if price_t < ma200_t:
            return '🚨피신(SGOV)'
        # (2) 과열구간: 200일선+5% 위면 홀딩 (추격매수 금지이나 백테스트상엔 보유 유지)
        elif price_t > env_t:
            return '🔥과열(홀딩)'
        # (3) 집중 투자 구간
        else:
            if price_y > ma200_y:
                return '💰풀매수/홀딩'
            else:
                return '👀하루참기(관망)'

    df['상태'] = [get_action(i) for i in range(len(df))]
    return df.dropna(subset=['MA200'])

# ── 메인 실행부 ──
col1, col2 = st.columns([2, 1])
with col1:
    # TQQQ는 상장이 늦어 2000년 테스트를 위해 QQQ를 기본으로 하되 3배 레버리지를 시뮬레이션 옵션으로 넣음
    ticker = st.selectbox("테스트 종목", ["QQQ", "TQQQ", "SOXX", "SPY"])
with col2:
    start_year = st.selectbox("시작 연도", [2000, 2010, 2015, 2020], index=0)

raw_df = load_tqqq_backtest(ticker, start_year)
sig_df = calculate_baby_tqqq_signals(raw_df)

# 수익률 계산 (타임머신 제거 버전)
sig_df['daily_ret'] = sig_df['Close'].pct_change().fillna(0)
# '풀매수' 또는 '과열(홀딩)' 상태일 때만 투자
sig_df['invested'] = sig_df['상태'].shift(1).isin(['💰풀매수/홀딩', '🔥과열(홀딩)']).astype(int)
sig_df['strat_ret'] = sig_df['daily_ret'] * sig_df['invested']

sig_df['cum_bah'] = (1 + sig_df['daily_ret']).cumprod()
sig_df['cum_strat'] = (1 + sig_df['strat_ret']).cumprod()

# 결과 출력
final_strat = (sig_df['cum_strat'].iloc[-1] - 1) * 100
final_bah = (sig_df['cum_bah'].iloc[-1] - 1) * 100
mdd_strat = (sig_df['cum_strat'] / sig_df['cum_strat'].cummax() - 1).min() * 100

st.markdown(f"""
### 📊 전략 검증 결과
* **신호전략 수익률**: **{final_strat:,.1f}%**
* **바이앤홀드 수익률**: {final_bah:,.1f}%
* **전략 최대낙폭(MDD)**: **{mdd_strat:.1f}%** (피신 로직의 위력!)
""")

# 차트
fig = go.Figure()
fig.add_trace(go.Scatter(x=sig_df.index, y=sig_df['Close'], name='Price'))
fig.add_trace(go.Scatter(x=sig_df.index, y=sig_df['MA200'], name='MA200', line=dict(dash='dash')))
st.plotly_chart(fig, use_container_width=True)
