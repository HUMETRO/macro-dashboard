import streamlit as st
import plotly.graph_objects as go
import sys
import os
import pandas as pd
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

# 🎨 카드형 스타일 CSS 주입
st.markdown("""
    <style>
    .metric-card {
        background-color: #ffffff;
        border-radius: 12px;
        padding: 20px;
        border: 1px solid #e1e4e8;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        margin-bottom: 15px;
        transition: transform 0.2s ease-in-out;
    }
    .metric-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 15px rgba(0,0,0,0.1);
    }
    .buy-signal { border-left: 8px solid #28a745; background-color: #f8fff9; }
    .sell-signal { border-left: 8px solid #dc3545; background-color: #fff8f8; }
    .wait-signal { border-left: 8px solid #ffc107; background-color: #fffdf5; }
    .ticker-name { font-size: 1.2rem; font-weight: bold; color: #1f2937; }
    .score-label { font-size: 0.85rem; color: #6b7280; }
    .score-value { font-size: 1.1rem; font-weight: 600; color: #111827; }
    </style>
    """, unsafe_allow_html=True)

st.title("📊 매크로경제 위험알리미")
st.markdown("---")

# [3] 데이터 로딩
@st.cache_data(ttl=300)
def load_all_data():
    return get_all_market_data()

with st.spinner("⏳ 데이터를 가져오는 중..."):
    all_data = load_all_data()
    df_sectors = calculate_sector_scores(all_data['sector_etfs'])
    df_individual = calculate_individual_metrics(all_data['individual_stocks'])
    df_core = calculate_core_sector_scores(all_data['core_sectors'])

# [4] 메인 상단 지표
if not df_sectors.empty:
    avg_l, avg_s = df_sectors['L-score'].mean(), df_sectors['S-score'].mean()
    c1, c2, c3 = st.columns(3)
    c1.metric("평균 L-score", f"{avg_l:.2f}", help="장기 체력")
    c2.metric("평균 S-score", f"{avg_s:.2f}", help="단기 기세")
    with c3:
        if avg_l > 0 and avg_s > 0: st.success("✅ 매수 신호 (상승장)")
        elif avg_l < 0 and avg_s < 0: st.error("🚨 버려 버려! (하락장)")
        else: st.warning("⚠️ 관망 (방향 탐색)")

# [5] 조기경보 시스템
top_5 = df_sectors.head(5)['섹터'].tolist()
safe_assets = ['CASH', '장기국채', '물가연동채', '유틸리티', '필수소비재']
safe_count = sum(1 for s in top_5 if s in safe_assets)
if safe_count >= 2:
    st.error(f"🚨 **안전자산 쏠림 경보!** 상위 5개 중 {safe_count}개가 방어 자산입니다. 스마트머니 피난 중!")
elif safe_count == 1:
    st.warning("⚠️ 안전자산 상승 주의: 상위권에 방어 자산 포착.")

# [6] 섹터 ETF 카드형 UI (혁신 포인트!)
st.subheader("📈 섹터 ETF 분석 (카드 뷰)")
if not df_sectors.empty:
    # PC에서는 3열, 모바일에서는 1열로 자동 조정되는 마법
    cols = st.columns(3) 
    for idx, row in df_sectors.iterrows():
        col_idx = idx % 3
        with cols[col_idx]:
            # 신호에 따른 클래스 결정
            sig_class = "buy-signal" if row['S-score'] > 0 and row['L-score'] > 0 else \
                        "sell-signal" if row['S-score'] < 0 and row['L-score'] < 0 else "wait-signal"
            
            st.markdown(f"""
                <div class="metric-card {sig_class}">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span class="ticker-name">{row['섹터']} ({row['티커']})</span>
                        <span style="font-weight: bold; color: {'#28a745' if row['20일(%)'] > 0 else '#dc3545'}">{row['20일(%)']}%</span>
                    </div>
                    <hr style="margin: 10px 0; border: 0.5px solid #eee;">
                    <div style="display: flex; justify-content: space-between;">
                        <div><span class="score-label">L-score</span><br><span class="score-value">{row['L-score']}</span></div>
                        <div><span class="score-label">S-score</span><br><span class="score-value">{row['S-score']}</span></div>
                        <div><span class="score-label">S-L</span><br><span class="score-value">{row['S-L']}</span></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

st.markdown("---")
# [7] 탭 구성 (기존 표 형식 유지 - 상세 분석용)
tab1, tab2 = st.tabs(["💹 개별 종목", "🎯 11개 핵심 섹터"])
with tab1:
    st.dataframe(df_individual.style.background_gradient(cmap='RdYlGn', subset=['연초대비', 'high대비', '200대비', '52저대비'], vmin=-10, vmax=10)
                 .format({'현재가': '{:.2f}', '연초대비': '{:.1f}%', 'high대비': '{:.1f}%', '200대비': '{:.1f}%', '전일대비': '{:.1f}%', '52저대비': '{:.1f}%'}),
                 use_container_width=True)

with tab2:
    st.dataframe(df_core.style.background_gradient(cmap='RdYlGn', subset=['S-SCORE', '20일(%)'])
                 .format({'S-SCORE': '{:.2f}', '20일(%)': '{:.2f}%'}), use_container_width=True)

# [8] 개별 섹터 차트 (MultiIndex 완벽 대응 - 수정본 유지)
st.markdown("---")
st.subheader("📉 개별 섹터 히스토리 차트")
selected = st.selectbox("섹터 선택", list(all_data['sector_etfs'].keys()))
if selected:
    hist = all_data['sector_etfs'][selected]['history'].copy()
    if isinstance(hist.columns, pd.MultiIndex):
        hist.columns = hist.columns.get_level_values(0)
    
    date_list = hist.index.tolist()
    close_list = hist['Close'].values.flatten() if isinstance(hist['Close'], pd.DataFrame) else hist['Close'].values

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=date_list, y=close_list, name='종가', line=dict(color='blue', width=2)))
    if 'MA20' in hist.columns:
        m20 = hist['MA20'].values.flatten() if isinstance(hist['MA20'], pd.DataFrame) else hist['MA20'].values
        fig.add_trace(go.Scatter(x=date_list, y=m20, name='MA20', line=dict(dash='dash', color='orange')))
    if 'MA200' in hist.columns:
        m200 = hist['MA200'].values.flatten() if isinstance(hist['MA200'], pd.DataFrame) else hist['MA200'].values
        fig.add_trace(go.Scatter(x=date_list, y=m200, name='MA200', line=dict(dash='dot', color='green', width=2)))
        
    fig.update_layout(title=f"{selected} ({all_data['sector_etfs'][selected]['ticker']}) 분석 차트", 
                      template="plotly_white", height=550, hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)
