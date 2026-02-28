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

# [2] 부품 로드 (MultiIndex 대응 헬퍼 포함)
try:
    from data_fetcher import get_all_market_data
    from calculations import calculate_sector_scores, calculate_individual_metrics, calculate_core_sector_scores
except ImportError as e:
    st.error(f"🚨 부품 로딩 실패! (에러: {e})")
    st.stop()

st.set_page_config(page_title="매크로 위험알리미", page_icon="📊", layout="wide")

# 🎨 카드형 스타일 CSS
st.markdown("""
    <style>
    .metric-card {
        background-color: #ffffff;
        border-radius: 12px;
        padding: 15px;
        border: 1px solid #e1e4e8;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        margin-bottom: 10px;
    }
    .buy-signal { border-left: 5px solid #28a745; background-color: #f8fff9; }
    .sell-signal { border-left: 5px solid #dc3545; background-color: #fff8f8; }
    .wait-signal { border-left: 5px solid #ffc107; background-color: #fffdf5; }
    .ticker-header { font-size: 1rem; font-weight: bold; margin-bottom: 5px; }
    .score-box { font-size: 0.8rem; color: #444; }
    </style>
    """, unsafe_allow_html=True)

st.title("📊 매크로경제 위험알리미")
st.markdown("---")

# [3] 데이터 로딩
@st.cache_data(ttl=300)
def load_all_data():
    return get_all_market_data()

with st.spinner("⏳ 실시간 데이터를 분석 중입니다..."):
    all_data = load_all_data()
    df_sectors = calculate_sector_scores(all_data['sector_etfs'])
    df_individual = calculate_individual_metrics(all_data['individual_stocks'])
    df_core = calculate_core_sector_scores(all_data['core_sectors'])

# [4] 상단 요약 대시보드
if not df_sectors.empty:
    avg_l, avg_s = df_sectors['L-score'].mean(), df_sectors['S-score'].mean()
    c1, c2, c3 = st.columns(3)
    c1.metric("평균 L-score (장기)", f"{avg_l:.2f}")
    c2.metric("평균 S-score (단기)", f"{avg_s:.2f}")
    with c3:
        if avg_l > 0 and avg_s > 0: st.success("✅ 매수 적기")
        elif avg_l < 0 and avg_s < 0: st.error("🚨 위험 신호")
        else: st.warning("⚠️ 관망 유지")

# [5] 섹터 ETF 탭 (하이브리드 UI 핵심)
st.markdown("### 📈 섹터 ETF 분석")
tab_card, tab_table = st.tabs(["🎴 카드 뷰 (기세 확인)", "📑 테이블 뷰 (정밀 정렬)"])

with tab_card:
    st.caption("💡 모바일에서 한눈에 섹터별 상태를 확인하기 좋습니다.")
    cols = st.columns(4) # PC 기준 4열 배치
    for idx, row in df_sectors.iterrows():
        with cols[idx % 4]:
            sig = "buy-signal" if row['S-score'] > 0 and row['L-score'] > 0 else \
                  "sell-signal" if row['S-score'] < 0 and row['L-score'] < 0 else "wait-signal"
            st.markdown(f"""
                <div class="metric-card {sig}">
                    <div class="ticker-header">{row['섹터']} <small style='color:gray;'>{row['티커']}</small></div>
                    <div class="score-box">
                        <b>S-L: {row['S-L']}</b> | 20일: {row['20일(%)']}%<br>
                        L: {row['L-score']} / S: {row['S-score']}
                    </div>
                </div>
                """, unsafe_allow_html=True)

with tab_table:
    st.caption("💡 상단 컬럼을 클릭하여 원하는 지표 순으로 정렬하십시오.")
    def highlight_benchmarks(row):
        sector = row['섹터']
        if sector in ['S&P', 'NASDAQ']: return ['background-color: #f0f2f6; font-weight: bold'] * len(row)
        elif sector in ['CASH', '물가연동채', '장기국채']: return ['background-color: #e2efda; color: #385723;'] * len(row)
        return [''] * len(row)

    st.dataframe(
        df_sectors.style.apply(highlight_benchmarks, axis=1)
        .background_gradient(cmap='RdYlGn', subset=['L-score', 'S-score', 'S-L', '20일(%)'])
        .format({'L-score': '{:.2f}', 'S-score': '{:.2f}', 'S-L': '{:.2f}', '20일(%)': '{:.2f}%'}),
        use_container_width=True, height=600
    )

# [6] 기타 탭 및 차트 (기존 유지)
st.markdown("---")
t1, t2 = st.tabs(["💹 개별 종목", "🎯 11개 핵심 섹터"])
with t1:
    st.dataframe(df_individual.style.background_gradient(cmap='RdYlGn', subset=['연초대비', 'high대비', '200대비', '52저대비'])
                 .format({'현재가': '{:.2f}', '연초대비': '{:.1f}%', 'high대비': '{:.1f}%', '200대비': '{:.1f}%', '전일대비': '{:.1f}%', '52저대비': '{:.1f}%'}), use_container_width=True)
with t2:
    st.dataframe(df_core.style.background_gradient(cmap='RdYlGn', subset=['S-SCORE', '20일(%)']).format({'S-SCORE': '{:.2f}', '20일(%)': '{:.2f}%'}), use_container_width=True)

# [7] 차트 (MultiIndex 대응 완료)
st.markdown("---")
selected = st.selectbox("상세 차트 선택", list(all_data['sector_etfs'].keys()))
if selected:
    hist = all_data['sector_etfs'][selected]['history'].copy()
    if isinstance(hist.columns, pd.MultiIndex): hist.columns = hist.columns.get_level_values(0)
    
    date_list = hist.index.tolist()
    # 💡 데이터 추출 시 DataFrame 형태가 되는 버그 방어
    def get_val(series): return series.values.flatten() if isinstance(series, pd.DataFrame) else series.values

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=date_list, y=get_val(hist['Close']), name='종가', line=dict(color='blue', width=2)))
    if 'MA20' in hist.columns: fig.add_trace(go.Scatter(x=date_list, y=get_val(hist['MA20']), name='MA20', line=dict(dash='dash', color='orange')))
    if 'MA200' in hist.columns: fig.add_trace(go.Scatter(x=date_list, y=get_val(hist['MA200']), name='MA200', line=dict(dash='dot', color='green')))
    
    fig.update_layout(title=f"{selected} 분석 차트", template="plotly_white", height=500, hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)
