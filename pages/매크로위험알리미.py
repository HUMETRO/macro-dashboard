import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import sys
import os
import numpy as np

# [1] 경로 설정: 상위 폴더의 부품 로드용
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
    st.info("💡 3년치 데이터를 기반으로 장단기 추세를 분석합니다")
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

# [5] 메인 시장 상태 지표 (디자인 복구)
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

st.caption("💡 **시장 판별:** 평균 L/S 스코어가 모두 **0보다 크면 '매수'**, 모두 **0보다 작으면 '버려'**, 그 외는 **'관망'**입니다.")

# 안전자산 쏠림 감지 (복구)
top_5_sectors = df_sectors.head(5)['섹터'].tolist()
safe_assets = ['CASH', '장기국채', '물가연동채', '유틸리티', '필수소
