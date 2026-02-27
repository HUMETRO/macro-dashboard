import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import sys
import os

# 상위 폴더 경로 설정 (Home 폴더의 부품 로드용)
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

try:
    from data_fetcher import get_all_market_data
    from calculations import calculate_sector_scores, calculate_individual_metrics, calculate_core_sector_scores
except ImportError as e:
    st.error(f"🚨 부품 로딩 실패! 경로를 확인하세요. (에러: {e})")
    st.stop()

st.set_page_config(page_title="매크로 위험알리미", page_icon="📊", layout="wide")

st.title("📊 매크로경제 위험알리미")
st.markdown("---")

# 사이드바 설정
with st.sidebar:
    st.info("💡 미국 섹터 ETF의 장단기 스코어를 분석합니다")
    if st.button("🔄 데이터 새로고침"):
        st.cache_data.clear()

# 데이터 로딩 (캐시 적용)
@st.cache_data(ttl=300)
def load_all_data():
    return get_all_market_data()

with st.spinner("⏳ 데이터 로딩 중..."):
    all_data = load_all_data()
    df_sectors = calculate_sector_scores(all_data['sector_etfs'])
    df_individual = calculate_individual_metrics(all_data['individual_stocks'])
    df_core = calculate_core_sector_scores(all_data['core_sectors'])

if 'L-score' not in df_sectors.columns or len(df_sectors) == 0:
    st.error("🚨 데이터를 불러오지 못했습니다.")
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
    if avg_l > 0 and avg_s > 0:
        st.success("✅ 매수 신호 (상승장)")
    elif avg_l < 0 and avg_s < 0:
        st.error("🚨 버려 버려! (하락장)")
    else:
        st.warning("⚠️ 관망 (방향 탐색)")

# 안전자산 쏠림 감지 경보
top_5_sectors = df_sectors.head(5)['섹터'].tolist()
safe_assets = ['CASH', '장기국채', '물가연동채', '유틸리티', '필수소비재']
safe_count = sum(1 for sector in top_5_sectors if sector in safe_assets)

if safe_count >= 2:
    st.error(f"🚨 **안전 자산 쏠림 경보!** 상위권에 방어적 자산 {safe_count}개 포착.")

st.markdown("---")

# 3개 탭 구성
tab1, tab2, tab3 = st.tabs(["📈 섹터 ETF", "💹 개별 종목", "🎯 11개 핵심 섹터"])

# === 탭1: 섹터 ETF ===
with tab1:
    st.subheader("📈 섹터 ETF 스코어 (S-L 순위)")
    
    subset_cols = ['L-score', 'S-score', 'S-L', '20일(%)']
    st.dataframe(
        df_sectors.style
            .background_gradient(cmap='RdYlGn', subset=subset_cols)
            .format({'R': '{:.0f}', 'L-score': '{:.2f}', 'S-score': '{:.2f}', 'S-L': '{:.2f}', '20일(%)': '{:.2f}%'}),
        use_container_width=True, height=600
    )
    
    st.markdown("##### 💡 퀀트 지표 요약")
    st.caption("1️⃣ **S-L:** 추세 가속도. 최근 한 달 사이 돈이 쏠리는 정도.")
    st.caption("2️⃣ **미너비니 필터:** 하락 추세 종목 순위 강등 로직 적용.")

# === 탭2: 개별 종목 ===
with tab2:
    st.subheader("💹 개별 종목 추적")
    numeric_cols = ['연초대비', 'high대비', '200대비', '전일대비', '52저대비']
    st.dataframe(
        df_individual.style
            .background_gradient(cmap='RdYlGn', subset=numeric_cols, vmin=-10, vmax=10)
            .format({'현재가': '{:.2f}', '연초대비': '{:.1f}%', 'high대비': '{:.1f}%', '200대비': '{:.1f}%', '전일대비': '{:.1f}%', '52저대비': '{:.1f}%'}, na_rep="N/A"),
        use_container_width=True, height=600
    )

# === 탭3: 11개 핵심 섹터 ===
with tab3:
    st.subheader("🎯 11개 핵심 섹터")
    st.dataframe(df_core.style.background_gradient(cmap='RdYlGn', subset=['S-SCORE']).format({'S-SCORE': '{:.2f}'}), use_container_width=True)

# === 개별 차트 (200일선 완벽 표시 버전) ===
st.markdown("---")
st.subheader("📉 개별 섹터 차트")
all_sectors = list(all_data['sector_etfs'].keys())
selected = st.selectbox("섹터 선택", all_sectors)

if selected and selected in all_data['sector_etfs']:
    # .tail() 없이 전체 3년 데이터를 사용하여 차트 시작점부터 MA200을 표시합니다.
    hist = all_data['sector_etfs'][selected]['history']
    ticker = all_data['sector_etfs'][selected]['ticker']
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=hist.index, y=hist['Close'], name='종가', line=dict(width=2, color='blue')))
    fig.add_trace(go.Scatter(x=hist.index, y=hist['MA20'], name='MA20', line=dict(dash='dash', color='orange')))
    fig.add_trace(go.Scatter(x=hist.index, y=hist['MA200'], name='MA200', line=dict(dash='dot', color='green')))
    
    # [핵심] 차트의 가독성을 위해 최근 약 1.5년(500일) 정도로 화면을 고정하지만, 
    # 데이터는 3년치라
