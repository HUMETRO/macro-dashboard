import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import yfinance as yf

st.set_page_config(page_title="커스텀 리포트", page_icon="🛡️", layout="wide")

# ── 스타일 설정 ──
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700&display=swap');
html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; }

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

st.title("🛡️ 하이브리드: 정밀 리포트")
st.caption("역사적 위기 검증 시스템을 통해 전략을 백테스트합니다.")

# ── 데이터 로딩 (완벽 복구 버그 픽스!) ──
@st.cache_data(ttl=3600, show_spinner=False)
def load_v8_custom_data(ticker, start_year):
    fetch_start = f"{start_year - 1}-01-01"
    
    # 💡 [핵심 해결] 데이터를 가져오자마자 시간대(Timezone) 꼬임을 날려버리는 만능 함수
    def get_clean_data(tkr):
        d = yf.download(tkr, start=fetch_start, interval='1d', progress=False)
        if isinstance(d.columns, pd.MultiIndex): 
            d.columns = d.columns.get_level_values(0)
        if not d.empty:
            d.index = pd.to_datetime(d.index).tz_localize(None) # 시간대 꼬임 영구 방지!
        return d
        
    df = get_clean_data(ticker)[['Close']].dropna()
    vix = get_clean_data("^VIX")
    ovx = get_clean_data("^OVX")
    tnx = get_clean_data("^TNX")
    irx = get_clean_data("^IRX")
    
    # 이제 마음 놓고 병합(Join)해도 20년 치 과거 데이터가 절대 증발하지 않습니다!
    combined = df.join(vix['Close'].to_frame('VIX'), how='inner')
    
    if not ovx.empty and 'Close' in ovx.columns:
        combined = combined.join(ovx['Close'].to_frame('OVX'), how='left')
    else:
        combined['OVX'] = 30
        
    if not tnx.empty and not irx.empty and 'Close' in tnx.columns and 'Close' in irx.columns:
        combined['Spread'] = (tnx['Close'] - irx['Close'])
    else:
        combined['Spread'] = 1.0
        
    combined['MA20'] = combined['Close'].rolling(20).mean()
    combined['MA50'] = combined['Close'].rolling(50).mean()
    combined['MA200'] = combined['Close'].rolling(200).mean()
    combined['VIX_MA5'] = combined['VIX'].rolling(5).mean()
    
    combined['OVX'] = combined['OVX'].fillna(30)
    combined['Spread'] = combined['Spread'].fillna(1.0)
    
    return combined.dropna(subset=['Close', 'VIX', 'MA200'])

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

# ── 메인 실행 ──
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

# =====================================================================
# 🎯 [100% 팩트 기반] 역사적 위기 구간 '실시간 자동 계산' 엔진 탑재
# =====================================================================
st.markdown("---")
st.markdown("#### 🎯 역사적 위기 회피 스토리텔링 (실시간 계산 팩트)")
st.caption(f"💡 아래 위기를 클릭하시면 알고리즘이 해당 기간 동안 <b>[{ticker}]</b> 폭락을 어떻게 피했는지 100% 실시간 데이터로 보여줍니다.")

# 💡 위기별 [시작일, 종료일, 요약설명] 정의 (가짜 데이터 영구 삭제!)
CRISIS_PERIODS = {
    "닷컴버블 붕괴": {
        "start": "2000-03-01", "end": "2002-10-31",
        "desc": "회사 이름에 '.com'만 붙어 있으면 폭등하다 붕괴한 광기의 시대입니다."
    },
    "리먼 브라더스 파산": {
        "start": "2007-10-01", "end": "2009-03-31",
        "desc": "서브프라임 모기지 사태로 인해 전 세계 금융 시스템이 마비된 사건입니다."
    },
    "미국 신용등급 강등": {
        "start": "2011-05-01", "end": "2011-10-31",
        "desc": "S&P가 미국 국가 신용등급을 강등시키며 글로벌 증시가 패닉에 빠진 사건입니다."
    },
    "미중 무역전쟁": {
        "start": "2018-09-01", "end": "2018-12-31",
        "desc": "파월의 금리인상 고집과 미중 무역분쟁이 겹쳐 크리스마스 이브까지 피를 흘렸던 바닥입니다."
    },
    "코로나 팬데믹 쇼크": {
        "start": "2020-02-01", "end": "2020-04-30",
        "desc": "코로나19 창궐로 인해 한 달 만에 글로벌 증시가 수직 낙하한 셧다운 장세입니다."
    },
    "인플레이션 하락장": {
        "start": "2022-01-01", "end": "2022-10-31",
        "desc": "미 연준(Fed)의 공격적인 금리 인상으로 인해 1년 내내 시장이 무너진 장기 침체장입니다."
    },
    "트럼프 글로벌 관세 쇼크": {
        "start": "2025-04-01", "end": "2025-05-31",
        "desc": "트럼프 행정부의 관세 부과 발표로 증시가 발작을 일으킨 후 V자로 반등한 장세입니다."
    }
}

# 🔄 CRISIS_PERIODS를 돌면서 실시간 수익률 계산 및 UI 생성
for name, info in CRISIS_PERIODS.items():
    s_date = pd.Timestamp(info['start'])
    e_date = pd.Timestamp(info['end'])
    
    # 1. 상단에서 선택한 연도(start_year) 이전의 위기면 화면에 안 띄움
    if e_date < perf_df.index[0] or s_date > perf_df.index[-1]:
        continue
        
    # 2. 해당 위기 구간의 데이터만 뚝 떼어내기 (Slice)
    period_df = perf_df.loc[(perf_df.index >= s_date) & (perf_df.index <= e_date)]
    
    # 데이터가 부족하면 패스
    if len(period_df) < 2:
        continue
        
    # 3. 💯 100% 팩트 기반 실시간 수익률 계산 로직!
    # 존버 수익률 = (구간 마지막날 종가 / 구간 첫날 종가) - 1
    bah_return = (period_df['Close'].iloc[-1] / period_df['Close'].iloc[0] - 1) * 100
    
    # 시스템 수익률 = (구간 마지막날 누적수익 / 구간 첫날 누적수익) - 1
    sys_return = (period_df['cum_strat'].iloc[-1] / period_df['cum_strat'].iloc[0] - 1) * 100
    
    # 4. 방어 결과에 따른 색상 및 텍스트 처리
    sys_color = "bt-buy" if sys_return > bah_return else "bt-highlight"
    win_text = "✨ 시장 방어 성공!" if sys_return > bah_return else "💧 시장 대비 열위"
    
    # 위기 시작 시점의 시스템 신호 가져오기
    first_signal = period_df['신호'].iloc[0]
    first_cms = period_df['CMS'].iloc[0]

    with st.expander(f"💣 {name} ({info['start'][:7]} ~ {info['end'][:7]})"):
        st.markdown(f"""
        <div class="bt-card">
            <div class="bt-title">📖 위기 요약</div>
            <div class="bt-text">{info['desc']}</div>
        </div>
        <div class="bt-card">
            <div class="bt-title">🤖 V8 시스템의 대응 신호 (구간 진입 시점)</div>
            <div class="bt-text">
                • 🚨 <b>최초 감지 신호:</b> <span style="font-weight:800; color:#b91c1c;">{first_signal}</span> <small>(CMS: {first_cms:.1f}점)</small><br>
                • 🛡️ <b>실시간 팩트 체크:</b> 위기 구간 동안 시스템이 시장의 실제 데이터를 기반으로 산출해 낸 누적 수익률입니다.
            </div>
        </div>
        <div class="bt-card">
            <div class="bt-title">📊 실제 구간 수익률 ({ticker} 기준) - {win_text}</div>
            <div class="bt-text">
                • 📉 <b>단순 존버 시:</b> <span class="bt-highlight">{bah_return:+.1f}%</span><br>
                • 📈 <b>V8 시스템 대응 시: <span class="{sys_color}">{sys_return:+.1f}%</span></b>
            </div>
        </div>
        """, unsafe_allow_html=True)
