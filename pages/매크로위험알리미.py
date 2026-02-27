import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import sys
import os
import numpy as np

# [1] 경로 설정
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# [2] 부품 로드
try:
    from data_fetcher import get_all_market_data
    from calculations import calculate_sector_scores, calculate_individual_metrics, calculate_core_sector_scores
except ImportError as e:
    st.error(f"🚨 부품 로딩 실패! (에러: {e})")
    st.stop()

st.set_page_config(page_title="매크로 위험알리미", page_icon="📊", layout="wide")

st.title("📊 매크로경제 위험알리미")
st.markdown("---")

# [3] 사이드바 설정
with st.sidebar:
    st.info("💡 미국 섹터 ETF의 장단기 스코어를 분석합니다")
    if st.button("🔄 데이터 새로고침"):
        st.cache_data.clear()
        st.success("캐시가 삭제되었습니다!")

# [4] 데이터 로딩
@st.cache_data(ttl=300)
def load_all_data():
    return get_all_market_data()

with st.spinner("⏳ 야후 파이낸스에서 3년치 데이터를 가져오는 중..."):
    all_data = load_all_data()
    df_sectors = calculate_sector_scores(all_data['sector_etfs'])
    df_individual = calculate_individual_metrics(all_data['individual_stocks'])
    df_core = calculate_core_sector_scores(all_data['core_sectors'])

if df_sectors is None or df_sectors.empty:
    st.error("🚨 데이터를 불러오지 못했습니다. 사이드바의 새로고침을 눌러주세요.")
    st.stop() 

# [5] 메인 시장 상태 지표
col1, col2, col3 = st.columns(3)
avg_l = df_sectors['L-score'].mean()
avg_s = df_sectors['S-score'].mean()

with col1:
    st.metric("평균 L-score", f"{avg_l:.2f}", delta="장기 추세", delta_color="off")
with col2:
    st.metric("평균 S-score", f"{avg_s:.2f}", delta="단기 모멘텀", delta_color="off")
with col3:
    if avg_l > 0 and avg_s > 0:
        st.success("✅ 매수 신호 (상승장)")
    elif avg_l < 0 and avg_s < 0:
        st.error("🚨 버려 버려! (하락장)")
    else:
        st.warning("⚠️ 관망 (방향 탐색)")

st.caption("💡 **시장 상태 판별 기준:** 전체 평균 장기/단기 스코어가 모두 **0보다 크면 '매수'**, 모두 **0보다 작으면 '버려'**, 그 외는 **'관망'**입니다. 객관적인 숫자를 믿으십시오.") [cite: 2026-02-22]

# 조기경보 시스템 원문 유지
top_5_sectors = df_sectors.head(5)['섹터'].tolist()
safe_assets = ['CASH', '장기국채', '물가연동채', '유틸리티', '필수소비재']
safe_count = sum(1 for sector in top_5_sectors if sector in safe_assets)

if safe_count >= 2:
    st.error(f"🚨 **안전자산 쏠림 경보 발령!** 현재 상위 5개 중 {safe_count}개가 방어적 자산입니다. 스마트머니가 피난 중입니다. 관망하십시오!")
elif safe_count == 1:
    st.warning("⚠️ **안전자산 상승 주의:** 상위 5위권 내에 방어적 자산이 포착되었습니다.")

st.markdown("---")

# [6] 3개 탭 구성
tab1, tab2, tab3 = st.tabs(["📈 섹터 ETF", "💹 개별 종목", "🎯 11개 핵심 섹터"])

# === 탭1: 섹터 ETF ===
with tab1:
    st.subheader("📈 섹터 ETF 스코어 (S-L 순위)")
    
    def highlight_benchmarks(row):
        sector = row['섹터']
        if sector in ['S&P', 'NASDAQ']:
            return ['background-color: #d9d9d9; font-weight: bold'] * len(row)
        elif sector in ['CASH', '물가연동채', '장기국채']:
            return ['background-color: #e2efda; color: #385723; font-weight: bold'] * len(row)
        return [''] * len(row)

    st.dataframe(
        df_sectors.style
            .apply(highlight_benchmarks, axis=1)
            .background_gradient(cmap='RdYlGn', subset=['L-score', 'S-score', 'S-L', '20일(%)'])
            .format({
                'L-score': '{:.2f}', 'S-score': '{:.2f}', 'S-L': '{:.2f}', '20일(%)': '{:.2f}%'
            }),
        use_container_width=True, height=600
    )
    
    st.markdown("##### 💡 퀀트 지표 핵심 요약")
    st.caption("1️⃣ **S-L:** 추세 가속도. 값이 클수록 최근 돈이 맹렬하게 몰리고 있음을 뜻합니다.")
    st.caption("2️⃣ **미너비니 필터:** 단기 추세(S)가 마이너스면 순위에서 강등시킵니다.")
    st.caption("3️⃣ **20일(%):** 최근 1개월간의 실제 수익률 성적표입니다.")

# === 탭2: 개별 종목 ===
with tab2:
    st.subheader("💹 개별 종목 추적 (위험도별 분류)")
    def highlight_risk(row):
        ticker = row['티커']
        if ticker in ['VOO', 'QQQ', 'AAPL', 'MSFT', 'GOOG', 'AMZN', 'AVGO']:
            return ['background-color: #e2efda; font-weight: bold'] * len(row) 
        elif ticker in ['SOXL', 'BULZ', 'IBIT']:
            return ['background-color: #f8cbad; color: #833c0c; font-weight: bold'] * len(row) 
        return [''] * len(row)

    # [수정] 52저대비 % 단위 및 소수점 한 자리 마감
    st.dataframe(
        df_individual.style
            .apply(highlight_risk, axis=1)
            .background_gradient(cmap='RdYlGn', subset=['연초대비', 'high대비', '200대비', '전일대비', '52저대비'], vmin=-10, vmax=10)
            .format({
                '현재가': '{:.2f}', 
                '연초대비': '{:.1f}%', 
                'high대비': '{:.1f}%', 
                '200대비': '{:.1f}%', 
                '전일대비': '{:.1f}%',
                '52저대비': '{:.1f}%' 
            }, na_rep="N/A"),
        use_container_width=True, height=600
    )
    st.caption("💡 **배경색 의미:** 🟩 코어 우량주 / 🟨 위성 자산 / 🟥 레버리지 및 고변동성")

# === 탭3: 11개 핵심 섹터 ===
with tab3:
    st.subheader("🎯 11개 핵심 섹터")
    st.dataframe(
        df_core.style.background_gradient(cmap='RdYlGn', subset=['S-SCORE'])
        .format({'S-SCORE': '{:.2f}'}), 
        use_container_width=True
    )

# === [7] 개별 차트 ===
st.markdown("---")
st.subheader("📉 개별 섹터 히스토리 차트")
selected = st.selectbox("섹터 선택", list(all_data['sector_etfs'].keys()))

if selected:
    hist = all_data['sector_etfs'][selected]['history']
    ticker = all_data['sector_etfs'][selected]['ticker']
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=hist.index, y=hist['Close'], name='종가', line=dict(width=2, color='blue')))
    fig.add_trace(go.Scatter(x=hist.index, y=hist['MA20'], name='MA20', line=dict(dash='dash', color='orange')))
    fig.add_trace(go.Scatter(x=hist.index, y=hist['MA200'], name='MA200', line=dict(dash='dot', color='green')))
    
    view_days = min(len(hist), 500)
    fig.update_layout(
        title=f"{selected} ({ticker}) 분석 차트",
        xaxis_range=[hist.index[-view_days], hist.index[-1]],
        template="plotly_white", 
        height=550,
        hovermode="x unified"
    )
    st.plotly_chart(fig, use_container_width=True)
