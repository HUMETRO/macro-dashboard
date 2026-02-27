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

# [2] 부품 로드 (에러 진단 보강)
try:
    from data_fetcher import get_all_market_data
    from calculations import calculate_sector_scores, calculate_individual_metrics, calculate_core_sector_scores
except ImportError as e:
    st.error(f"🚨 라이브러리 혹은 부품 로딩 실패: {e}")
    st.stop()

st.set_page_config(page_title="매크로 위험알리미", page_icon="📊", layout="wide")

st.title("📊 매크로경제 위험알리미")
st.markdown("---")

# [3] 사이드바
with st.sidebar:
    st.info("💡 3년치 데이터를 기반으로 MA200을 완벽 분석합니다.")
    if st.button("🔄 캐시 강제 초기화"):
        st.cache_data.clear()
        st.success("캐시를 비웠습니다. 새로고침을 해주세요!")

# [4] 데이터 로딩 로직 (에러 발생 시 상세 정보 출력)
@st.cache_data(ttl=300)
def load_all_data():
    try:
        return get_all_market_data()
    except Exception as e:
        st.error(f"❌ 데이터 수집 중 오류 발생: {e}")
        return None

with st.spinner("⏳ 야후 파이낸스에서 3년치 데이터를 긁어오는 중..."):
    all_data = load_all_data()
    
    if all_data:
        try:
            df_sectors = calculate_sector_scores(all_data['sector_etfs'])
            df_individual = calculate_individual_metrics(all_data['individual_stocks'])
            df_core = calculate_core_sector_scores(all_data['core_sectors'])
        except Exception as e:
            st.error(f"❌ 데이터 계산 중 오류 발생: {e}")
            st.stop()
    else:
        st.error("🚨 시장 데이터를 가져오지 못했습니다. 잠시 후 다시 시도해주세요.")
        st.stop()

# 데이터 검증
if df_sectors is None or df_sectors.empty:
    st.error("🚨 섹터 스코어 데이터가 비어있습니다.")
    st.stop()

# === [5] 메인 화면 지표 ===
col1, col2, col3 = st.columns(3)
avg_l = df_sectors['L-score'].mean()
avg_s = df_sectors['S-score'].mean()

with col1:
    st.metric("평균 L-score", f"{avg_l:.2f}")
with col2:
    st.metric("평균 S-score", f"{avg_s:.2f}")
with col3:
    if avg_l > 0 and avg_s > 0:
        st.success("✅ 매수 신호")
    elif avg_l < 0 and avg_s < 0:
        st.error("🚨 위험 (관망/매도)")
    else:
        st.warning("⚠️ 관망")

st.markdown("---")

# [6] 탭 구성 및 데이터 출력
tab1, tab2, tab3 = st.tabs(["📈 섹터 ETF", "💹 개별 종목", "🎯 11개 핵심 섹터"])

with tab1:
    st.dataframe(df_sectors, use_container_width=True)

with tab2:
    st.dataframe(df_individual, use_container_width=True)

with tab3:
    st.dataframe(df_core, use_container_width=True)

# [7] 개별 차트 (200일선 왼쪽 끝까지 채우기)
st.markdown("---")
st.subheader("📉 개별 섹터 차트 분석")
selected = st.selectbox("섹터 선택", list(all_data['sector_etfs'].keys()))

if selected:
    hist = all_data['sector_etfs'][selected]['history']
    ticker = all_data['sector_etfs'][selected]['ticker']
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=hist.index, y=hist['Close'], name='종가', line=dict(color='blue')))
    fig.add_trace(go.Scatter(x=hist.index, y=hist['MA20'], name='MA20', line=dict(dash='dash', color='orange')))
    fig.add_trace(go.Scatter(x=hist.index, y=hist['MA200'], name='MA200', line=dict(dash='dot', color='green')))
    
    # 데이터가 3년치(약 750일)이므로, 최근 500거래일(약 2년)을 보여주면 200일선은 완벽히 나옵니다.
    view_days = min(len(hist), 500)
    fig.update_layout(
        title=f"{selected} ({ticker}) 히스토리",
        xaxis_range=[hist.index[-view_days], hist.index[-1]],
        template="plotly_white",
        height=550
    )
    st.plotly_chart(fig, use_container_width=True)
