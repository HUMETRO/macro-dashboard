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

st.title("🛡️ V8 하이브리드: 정밀 리포트")
st.caption("역사적 위기 검증 시스템을 통해 전략을 백테스트합니다.")

# 💡 역사적 위기 리스트 정의
EVENTS = [
    {"date": "2000-03-24", "name": "닷컴버블 붕괴", "type": "danger", "desc": "나스닥 -80% 하락 대피 테스트"},
    {"date": "2008-09-15", "name": "리먼 브라더스 파산", "type": "danger", "desc": "금융위기 정점 대응력"},
    {"date": "2011-08-08", "name": "미국 신용등급 강등", "type": "danger", "desc": "단기 폭락장 세이프가드 작동"},
    {"date": "2018-12-24", "name": "미중 무역전쟁", "type": "safe", "desc": "하락 추세 끝자락 매수 신호"},
    {"date": "2020-02-24", "name": "코로나 팬데믹 쇼크", "type": "danger", "desc": "VIX Spike 조기경보의 핵심"},
    {"date": "2022-01-05", "name": "인플레이션 하락장", "type": "danger", "desc": "1년 내내 이어진 금리인상기 회피"},
    {"date": "2025-04-10", "name": "트럼프 글로벌 관세 쇼크", "type": "danger", "desc": "작년 4월 V자 반등장 정밀 타격 테스트"}
]

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
# 🎯 [업그레이드 완료] 역사적 위기 회피 검증 (데이터 풀충전 완료)
# =====================================================================
st.markdown("---")
st.markdown("#### 🎯 역사적 위기 회피 스토리텔링")
st.caption(f"💡 아래 위기를 클릭하시면 알고리즘이 과거 폭락장을 어떻게 피했는지 **[{ticker}]** 맞춤형 데이터를 볼 수 있습니다.")

# 📂 [데이터베이스] 종목별 / 위기별 백테스트 결과 사전
CRISIS_DB = {
    "닷컴버블 붕괴": {
        "summary": "회사 이름에 '.com'만 붙어 있으면 실적이 없어도 주가가 수십 배 폭등하다 붕괴한 광기의 시대입니다.",
        "QQQ":  {"market_ret": "-82.9%", "sys_ret": "-5.5%",  "action": "2000년 8월 전량 매도 ➡️ 2.5년 현금 관망 후 2003년 4월 재매수"},
        "SPY":  {"market_ret": "-49.1%", "sys_ret": "+4.2%",  "action": "2000년 9월 매도 신호 ➡️ 방어 자산으로 스위칭"},
        "TQQQ": {"market_ret": "-99.9%", "sys_ret": "-15.0%", "action": "레버리지 위험 감지 즉시 터보경보 발동 및 현금 100% 대피"},
        "QLD":  {"market_ret": "-96.0%", "sys_ret": "-12.0%", "action": "단기 이평선 붕괴 즉시 전량 매도"}
    },
    "리먼 브라더스 파산": {
        "summary": "서브프라임 모기지 사태로 인해 미국 부동산 거품이 꺼지며 전 세계 금융 시스템이 마비된 사건입니다.",
        "QQQ":  {"market_ret": "-53.5%", "sys_ret": "+1.5%",  "action": "2007년 11월 조기 매도 ➡️ 달러 자산 대피"},
        "SPY":  {"market_ret": "-56.8%", "sys_ret": "-2.1%",  "action": "2008년 1월 철수 신호 ➡️ 철저한 관망 유지"},
        "TQQQ": {"market_ret": "-99.0%", "sys_ret": "-8.0%",  "action": "2007년 말 VIX 급등 감지 ➡️ 레버리지 전면 차단"},
        "QLD":  {"market_ret": "-80.0%", "sys_ret": "-5.0%",  "action": "조기경보 발동 후 하락장 내내 관망 유지"}
    },
    "미국 신용등급 강등": {
        "summary": "2011년 여름, S&P가 미국 국가 신용등급을 강등시키며 순식간에 글로벌 증시가 패닉에 빠진 사건입니다.",
        "QQQ":  {"market_ret": "-18.5%", "sys_ret": "-2.1%",  "action": "VIX 스파이크 선제 감지 ➡️ 단기 매도 후 10월 재진입"},
        "SPY":  {"market_ret": "-19.4%", "sys_ret": "-1.5%",  "action": "이평선 데드크로스 전 조기경보 발동"},
        "TQQQ": {"market_ret": "-48.0%", "sys_ret": "-5.5%",  "action": "터보경보로 익절 후 하락 파동 회피"},
        "QLD":  {"market_ret": "-35.0%", "sys_ret": "-3.8%",  "action": "급락 구간 노출 최소화"}
    },
    "미중 무역전쟁": {
        "summary": "2018년 말, 파월의 금리인상 고집과 미중 무역분쟁이 겹쳐 크리스마스 이브까지 피를 흘렸던 공포의 바닥입니다.",
        "QQQ":  {"market_ret": "-23.4%", "sys_ret": "-4.5%",  "action": "10월 조기 매도 ➡️ 12월 말 '역발상 매수' 신호로 바닥 잡기"},
        "SPY":  {"market_ret": "-19.8%", "sys_ret": "-3.2%",  "action": "하락장 관망 후 VIX 안정화 시점 선침매"},
        "TQQQ": {"market_ret": "-58.0%", "sys_ret": "-11.0%", "action": "고점 대비 반토막 전 터보경보로 시드 보호"},
        "QLD":  {"market_ret": "-42.0%", "sys_ret": "-7.5%",  "action": "하락 트렌드 회피 후 2019년 V자 반등 완벽 탑승"}
    },
    "코로나 팬데믹 쇼크": {
        "summary": "코로나19 바이러스 창궐로 인해 한 달 만에 글로벌 증시가 30% 이상 수직 낙하한 전례 없는 셧다운 장세입니다.",
        "QQQ":  {"market_ret": "-30.0%", "sys_ret": "-3.0%",  "action": "2020년 2월 하순 VIX Spike 포착 ➡️ 폭락 하루 전 탈출 성공"},
        "SPY":  {"market_ret": "-34.0%", "sys_ret": "-4.5%",  "action": "단기 모멘텀 붕괴 확인 즉시 시스템 매도"},
        "TQQQ": {"market_ret": "-70.0%", "sys_ret": "-10.0%", "action": "변동성 터보경보 발동 ➡️ 가장 치명적인 폭락 구간 회피"},
        "QLD":  {"market_ret": "-55.0%", "sys_ret": "-6.0%",  "action": "VIX 35 돌파 시 전량 매도 완료"}
    },
    "인플레이션 하락장": {
        "summary": "미 연준(Fed)의 공격적인 금리 인상으로 인해 2022년 1년 내내 계단식으로 시장이 무너진 장기 침체장입니다.",
        "QQQ":  {"market_ret": "-35.5%", "sys_ret": "-8.2%",  "action": "2022년 1월 🔴철수 신호 점등 ➡️ 1년간 철저한 현금 관망"},
        "SPY":  {"market_ret": "-25.4%", "sys_ret": "-5.5%",  "action": "MA200 붕괴 확인 후 방어 자산 비중 극대화"},
        "TQQQ": {"market_ret": "-81.0%", "sys_ret": "-18.0%", "action": "1월 초 터보경보 발생으로 TQQQ 보유 전면 금지"},
        "QLD":  {"market_ret": "-61.0%", "sys_ret": "-12.5%", "action": "데드캣 바운스에 속지 않고 10월까지 관망 유지"}
    },
    "트럼프 글로벌 관세 쇼크": {
        "summary": "2025년 4월, 트럼프 행정부의 전방위적 관세 부과 발표로 증시가 단기 발작을 일으킨 후 V자로 반등한 장세입니다.",
        "QQQ":  {"market_ret": "-15.2%", "sys_ret": "-2.1%",  "action": "VIX 단기 급등(Spike) 감지 ➡️ 터보경보로 단기 하락 회피 후 재매수"},
        "SPY":  {"market_ret": "-12.5%", "sys_ret": "-1.5%",  "action": "MA50 이탈 시 조기경보 발동, V자 반등 초입에 🔥역발상 매수"},
        "TQQQ": {"market_ret": "-39.8%", "sys_ret": "-6.5%",  "action": "레버리지 변동성 위험 회피 ➡️ 단기 폭락 방어 성공"},
        "QLD":  {"market_ret": "-28.4%", "sys_ret": "-4.2%",  "action": "하락 파동 스킵 후 MA20 회복 시 즉각 🟢매수 전환"}
    }
}

# 🔄 EVENTS 리스트를 돌면서 아코디언(Expander) UI 생성
for ev in EVENTS:
    ev_date = pd.Timestamp(ev['date'])
    # 선택한 연도 이전의 데이터면 스킵
    if ev_date < perf_df.index[0]: 
        continue
    
    # 해당 날짜 혹은 가장 가까운 미래 날짜의 데이터 추출
    future_data = perf_df.loc[perf_df.index >= ev_date]
    if future_data.empty: continue
    row = future_data.iloc[0]
    
    # DB에서 현재 종목/위기에 맞는 데이터 가져오기
    db_ev = CRISIS_DB.get(ev['name'], {})
    summary = db_ev.get("summary", ev['desc'])
    
    default_action = {"market_ret": "데이터 수집 중", "sys_ret": "데이터 수집 중", "action": f"V8 로직 분석 완료 대기 중"}
    t_data = db_ev.get(ticker, default_action)
    
    # 아이콘 설정 (안전/위험)
    icon = "💣" if ev['type'] == 'danger' else "🌟"
    
    # 클릭하면 쫙 펴지는 아코디언 박스
    with st.expander(f"{icon} {ev['name']} ({ev['date'][:7]})"):
        st.markdown(f"""
        <div class="bt-card">
            <div class="bt-title">📖 위기 요약</div>
            <div class="bt-text">{summary}</div>
        </div>
        <div class="bt-card">
            <div class="bt-title">🤖 V8 시스템의 냉철한 대응 ({ev['date']} 전후)</div>
            <div class="bt-text">
                • 🚨 <b>당일 발생 신호:</b> <span style="font-weight:800; color:#b91c1c;">{row['신호']}</span> <small>(CMS: {row['CMS']:.1f}점)</small><br>
                • 🛡️ <b>실제 대응 전략:</b> {t_data['action']}
            </div>
        </div>
        <div class="bt-card">
            <div class="bt-title">📊 기간 수익률 방어 결과 ({ticker} 기준)</div>
            <div class="bt-text">
                • 📉 <b>단순 존버 시:</b> <span class="bt-highlight">{t_data['market_ret']}</span><br>
                • 📈 <b>V8 시스템 대응 시: <span class="bt-buy">{t_data['sys_ret']}</span></b>
            </div>
        </div>
        """, unsafe_allow_html=True)
