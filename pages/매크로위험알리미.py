import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import sys
import os

# [강력 처방] 상위 폴더(Home)에 있는 data_fetcher와 calculations를 찾을 수 있게 경로를 강제 지정합니다.
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

try:
    from data_fetcher import get_all_market_data
    from calculations import calculate_sector_scores, calculate_individual_metrics, calculate_core_sector_scores
except ImportError as e:
    st.error(f"🚨 부품 로딩 실패! 관리자에게 문의하세요. (에러: {e})")
    st.stop()

st.set_page_config(page_title="매크로 위험알리미", page_icon="📊", layout="wide")

st.title("📊 매크로경제 위험알리미")
st.markdown("---")

# 사이드바
with st.sidebar:
    st.info("💡 미국 섹터 ETF의 장단기 스코어를 분석합니다")
    if st.button("🔄 데이터 새로고침"):
        st.cache_data.clear()

# 데이터 로딩
@st.cache_data(ttl=300)
def load_all_data():
    return get_all_market_data()

with st.spinner("⏳ 데이터 로딩 중..."):
    all_data = load_all_data()
    
    df_sectors = calculate_sector_scores(all_data['sector_etfs'])
    df_individual = calculate_individual_metrics(all_data['individual_stocks'])
    df_core = calculate_core_sector_scores(all_data['core_sectors'])

if 'L-score' not in df_sectors.columns or len(df_sectors) == 0:
    st.error("🚨 인터넷 연결 문제 혹은 야후 파이낸스 서버 오류로 데이터를 가져오지 못했습니다. 터미널의 에러 로그를 확인해주세요.")
    st.stop() 

# === 메인 시장 상태 지표 ===
col1, col2, col3 = st.columns(3)
avg_l = df_sectors['L-score'].mean()
avg_s = df_sectors['S-score'].mean()

with col1:
    st.metric("평균 L-score", f"{avg_l:.2f}", delta="장기 추세", delta_color="off")
with col2:
    st.metric("평균 S-score", f"{avg_s:.2f}", delta="단기 모멘텀", delta_color="off")
with col3:
    if avg_l < 0 and avg_s < 0:
        st.error("🚨 버려 버려! (하락장)")
    elif avg_l > 0 and avg_s > 0:
        st.success("✅ 매수 신호 (상승장)")
    else:
        st.warning("⚠️ 관망 (방향 탐색)")

st.caption("💡 **시장 상태 판별 기준:** 30개 전체 섹터의 평균 장기/단기 스코어가 모두 **0보다 크면 '매수'**, 모두 **0보다 작으면 '버려(위험)'**, 그 외는 **'관망'**으로 표시됩니다. 감정에 휘둘리지 말고 객관적인 숫자를 믿으십시오.")

# 안전자산 쏠림 감지 조기경보 시스템
top_5_sectors = df_sectors.head(5)['섹터'].tolist()
safe_assets = ['CASH', '장기국채', '물가연동채', '유틸리티', '필수소비재']
safe_count = sum(1 for sector in top_5_sectors if sector in safe_assets)

if safe_count >= 2:
    st.error(f"🚨 **안전자산 쏠림 경보 발령!** 현재 상위 5개 섹터 중 {safe_count}개가 방어적 자산입니다. 시장의 스마트머니가 위험을 피해 피난하고 있습니다. 주식 비중 확대를 멈추고 관망하십시오!")
elif safe_count == 1:
    st.warning("⚠️ **안전자산 상승 주의:** 상위 5위권 내에 방어적 자산이 포착되었습니다. 시장의 변동성에 대비하십시오.")

st.markdown("---")

# 3개 탭으로 분리
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
        elif sector == '타임폴리오':
            return ['background-color: #d9e1f2; font-weight: bold'] * len(row)
        return [''] * len(row)

    subset_cols = ['L-score', 'S-score', 'S-L', '20일(%)']
    
    st.dataframe(
        df_sectors.style
            .apply(highlight_benchmarks, axis=1) 
            .background_gradient(cmap='RdYlGn', subset=subset_cols) 
            .format({
                'R': '{:.0f}',
                'L-score': '{:.2f}',
