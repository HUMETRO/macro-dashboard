import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import sys
import os
import numpy as np

# [1] 경로 설정: 상위 폴더의 data_fetcher, calculations를 찾기 위함
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# [2] 부품 로드 (Import 에러 방어)
try:
    from data_fetcher import get_all_market_data
    from calculations import calculate_sector_scores, calculate_individual_metrics, calculate_core_sector_scores
except ImportError as e:
    st.error(f"🚨 부품 로딩 실패! 파일 경로를 확인하세요. (에러: {e})")
    st.stop()

st.set_page_config(page_title="매크로 위험알리미", page_icon="📊", layout="wide")

st.title("📊 매크로경제 위험알리미")
st.markdown("---")

# [3] 사이드바: 데이터 관리
with st.sidebar:
    st.header("⚙️ 시스템 설정")
    st.info("💡 차트의 200일선(MA200)을 완벽히 구현하기 위해 3년치 데이터를 분석 중입니다.")
    if st.button("🔄 캐시 강제 초기화"):
        st.cache_data.clear()
        st.success("캐시가 비워졌습니다. 새로고침(F5)을 눌러주세요!")

# [4] 데이터 로딩 (에러 진단 로직 포함)
@st.cache_data(ttl=300)
def load_all_data():
    try:
        data = get_all_market_data()
        if not data or not data.get('sector_etfs'):
            return None
        return data
    except Exception as e:
        st.error(f"❌ 데이터 수집 중 서버 에러 발생: {e}")
        return None

with st.spinner("⏳ 야후 파이낸스에서 3년치 데이터를 긁어오고 있습니다... 최대 30초가 소요될 수 있습니다."):
    all_data = load_all_data()
    
    if all_data:
        try:
            # 계산기 가동
            df_sectors = calculate_sector_scores(all_data['sector_etfs'])
            df_individual = calculate_individual_metrics(all_data['individual_stocks'])
            df_core = calculate_core_sector_scores(all_data['core_sectors'])
        except Exception as e:
            st.error(f"❌ 데이터 계산 단계 오류: {e}")
            st.stop()
    else:
        st.warning("⚠️ 데이터를 아직 불러오지 못했습니다. 사이드바의 [캐시 강제 초기화]를 누르고 잠시만 기다려 주세요.")
        st.stop()

# [5] 메인 시장 상태 지표
if df_sectors is not None and not df_sectors.empty:
    col1, col2, col3 = st.columns(3)
    avg_l = df_sectors['L-score'].mean()
    avg_s = df_sectors['S-score'].mean()

    with col1:
        st.metric("평균 L-score", f"{avg_l:.2f}", help="장기 추세 점수 (0보다 크면 우상향)")
    with col2:
        st.metric("평균 S-score", f"{avg_s:.2f}", help="단기 모멘텀 점수 (0보다 크면 상승세)")
    with col3:
        if avg_l > 0 and avg_s > 0:
            st.success("✅ 매수 신호 (강세장)")
        elif avg_l < 0 and avg_s < 0:
            st.error("🚨 버려 버려! (약세장)")
        else:
            st.warning("⚠️ 관망 (혼조세)")
else:
    st.error("🚨 섹터 스코어 계산 결과가 비어있습니다. 데이터 수집을 다시 시도합니다.")
    st.stop()

st.markdown("---")

# [6] 데이터 분석 탭
tab1, tab2, tab3 = st.tabs(["📈 섹터 ETF 분석", "💹 개별 종목 상태", "🎯 11개 핵심 섹터"])

with tab1:
    st.subheader("📈 섹터별 퀀트 순위표")
    st.dataframe(df_sectors.style.background_gradient(cmap='RdYlGn', subset=['L-score', 'S-score', 'S-L']), use_container_width=True, height=500)

with tab2:
    st.subheader("💹 주요 종목 모니터링")
    st.dataframe(df_individual.style.background_gradient(cmap='RdYlGn', subset=['연초대비', '200대비', '전일대비']), use_container_width=True, height=500)

with tab3:
    st.subheader("🎯 S&P 500 11대 핵심 섹터")
    st.dataframe(df_core, use_container_width=True)

# [7] 개별 섹터 차트 (MA200 왼쪽 끝까지 채우기)
st.markdown("---")
st.subheader("📉 개별 섹터 히스토리 차트")
selected_sector = st.selectbox("분석할 섹터를 선택하세요", list(all_data['sector_etfs'].keys()))

if selected_sector:
    hist_df = all_data['sector_etfs'][selected_sector]['history']
    ticker_symbol = all_data['sector_etfs'][selected_sector]['ticker']
    
    fig = go.Figure()
    # 3년치 전체 데이터 표시
    fig.add_trace(go.Scatter(x=hist_df.index, y=hist_df['Close'], name='현재가', line=dict(color='#1f77b4', width=2)))
    fig.add_trace(go.Scatter(x=hist_df.index, y=hist_df['MA20'], name='20일선(단기)', line=dict(dash='dash', color='orange')))
    fig.add_trace(go.Scatter(x=hist_df.index, y=hist_df['MA200'], name='200일선(장기)', line=dict(dash='dot', color='green')))
    
    # 최근 2년(약 500거래일)을 기본 뷰로 설정하되, 200일선은 이미 계산된 상태로 노출
    visible_days = min(len(hist_df), 500)
    fig.update_layout(
        title=f"{selected_sector} ({ticker_symbol}) 기술적 분석",
        xaxis_range=[hist_df.index[-visible_days], hist_df.index[-1]],
        template="plotly_white",
        height=600,
        hovermode="x unified"
    )
    st.plotly_chart(fig, use_container_width=True)
