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

with st.spinner("⏳ 데이터를 가져오는 중..."):
    all_data = load_all_data()
    df_sectors = calculate_sector_scores(all_data['sector_etfs'])
    df_individual = calculate_individual_metrics(all_data['individual_stocks'])
    df_core = calculate_core_sector_scores(all_data['core_sectors'])

# [4] 메인 시장 상태 지표
if not df_sectors.empty and 'L-score' in df_sectors.columns:
    col1, col2, col3 = st.columns(3)
    avg_l = df_sectors['L-score'].mean()
    avg_s = df_sectors['S-score'].mean()
    with col1: st.metric("평균 L-score", f"{avg_l:.2f}", delta="장기 체력", delta_color="off")
    with col2: st.metric("평균 S-score", f"{avg_s:.2f}", delta="단기 기세", delta_color="off")
    with col3:
        if avg_l > 0 and avg_s > 0: st.success("✅ 매수 신호 (상승장)")
        elif avg_l < 0 and avg_s < 0: st.error("🚨 버려 버려! (하락장)")
        else: st.warning("⚠️ 관망 (방향 탐색)")
    
    st.caption("💡 시장 상태 판별 기준: 전체 평균 장기/단기 스코어가 모두 0보다 크면 '매수', 모두 0보다 작으면 '버려', 그 외는 '관망'입니다. 객관적인 숫자를 믿으십시오.")
else:
    st.error("🚨 데이터 계산 오류 발생!")

# [5] 조기경보 시스템
top_5_sectors = df_sectors.head(5)['섹터'].tolist()
safe_assets = ['CASH', '장기국채', '물가연동채', '유틸리티', '필수소비재']
safe_count = sum(1 for sector in top_5_sectors if sector in safe_assets)
if safe_count >= 2:
    st.error(f"🚨 **안전자산 쏠림 경보!** 상위 5개 중 {safe_count}개가 방어 자산입니다. 스마트머니가 피난 중입니다. 관망하십시오!")
elif safe_count == 1:
    st.warning("⚠️ **안전자산 상승 주의:** 상위권에 방어 자산이 포착되었습니다.")

st.markdown("---")

# [6] 하이브리드 UI (카드 + 테이블 + 기존 문구 복구)
tab1, tab2, tab3 = st.tabs(["📈 섹터 ETF", "💹 개별 종목", "🎯 11개 핵심 섹터"])

with tab1:
    st.subheader("📈 섹터 ETF 분석")
    
    # 카드 뷰와 테이블 뷰를 선택해서 볼 수 있게 하위 탭 구성
    sub_tab1, sub_tab2 = st.tabs(["🎴 카드 뷰", "📑 테이블 뷰"])
    
    with sub_tab1:
        cols = st.columns(4)
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

    with sub_tab2:
        def highlight_benchmarks(row):
            sector = row['섹터']
            if sector in ['S&P', 'NASDAQ']: return ['background-color: #d9d9d9; font-weight: bold'] * len(row)
            elif sector in ['CASH', '물가연동채', '장기국채']: return ['background-color: #e2efda; color: #385723; font-weight: bold'] * len(row)
            return [''] * len(row)
            
        st.dataframe(df_sectors.style.apply(highlight_benchmarks, axis=1)
                     .background_gradient(cmap='RdYlGn', subset=['L-score', 'S-score', 'S-L', '20일(%)'])
                     .format({'L-score': '{:.2f}', 'S-score': '{:.2f}', 'S-L': '{:.2f}', '20일(%)': '{:.2f}%'}),
                     use_container_width=True, height=500)

    # ⭐ [사라졌던 문구 복구!]
    st.markdown("##### 💡 퀀트 지표 핵심 요약")
    st.caption("**📊 L-score (장기 체력)**: 200일선 이격도, 52주 고점 위치 등을 종합한 장기 추세 점수입니다.")
    st.caption("**🚀 S-score (단기 기세)**: 20일선 이격도, 1개월 수익률 등을 종합한 단기 모멘텀 점수입니다.")
    st.caption("---")
    st.caption("1️⃣ **S-L (추세 가속도):** 단기 모멘텀(S)에서 장기 모멘텀(L)을 뺀 값입니다. 값이 클수록 최근 돈이 맹렬하게 몰리고 있음을 뜻합니다.")
    st.caption("2️⃣ **미너비니 절대 추세 필터 (랭킹 보정)**")
    st.caption("- 단기 추세(S-score)가 마이너스(-)인 섹터는 '하락 추세 속의 일시적 반등'일 뿐입니다.")
    st.caption("- 이런 '떨어지는 칼날'은 가짜 신호로 간주하여 순위표 최하위권으로 강제 강등시켰습니다.")
    st.caption("3️⃣ **20일(%):** 최근 1개월간의 실제 수익률 성적표입니다.")

with tab2:
    st.subheader("💹 개별 종목 추적")
    st.dataframe(df_individual.style.background_gradient(cmap='RdYlGn', subset=['연초대비', 'high대비', '200대비', '52저대비'], vmin=-10, vmax=10)
                 .format({'현재가': '{:.2f}', '연초대비': '{:.1f}%', 'high대비': '{:.1f}%', '200대비': '{:.1f}%', '전일대비': '{:.1f}%', '52저대비': '{:.1f}%'}),
                 use_container_width=True)

with tab3:
    st.subheader("🎯 11개 핵심 섹터")
    st.dataframe(df_core.style.background_gradient(cmap='RdYlGn', subset=['S-SCORE', '20일(%)'])
                 .format({'S-SCORE': '{:.2f}', '20일(%)': '{:.2f}%'}), use_container_width=True)

# [7] 차트 (로컬 날짜/MultiIndex 완벽 대응)
st.markdown("---")
st.subheader("📉 개별 섹터 히스토리 차트")
selected = st.selectbox("섹터 선택", list(all_data['sector_etfs'].keys()))
if selected:
    hist = all_data['sector_etfs'][selected]['history'].copy()
    if isinstance(hist.columns, pd.MultiIndex):
        hist.columns = hist.columns.get_level_values(0)
    
    date_list = hist.index.tolist()
    # 💡 로컬 렌더링을 위한 데이터 추출 헬퍼
    def get_val(series): return series.values.flatten() if isinstance(series, pd.DataFrame) else series.values

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=date_list, y=get_val(hist['Close']), name='종가', line=dict(color='blue', width=2)))
    if 'MA20' in hist.columns:
        fig.add_trace(go.Scatter(x=date_list, y=get_val(hist['MA20']), name='MA20', line=dict(dash='dash', color='orange')))
    if 'MA200' in hist.columns:
        fig.add_trace(go.Scatter(x=date_list, y=get_val(hist['MA200']), name='MA200', line=dict(dash='dot', color='green', width=2)))
        
    view_days = min(len(hist), 500)
    fig.update_layout(
        title=f"{selected} ({all_data['sector_etfs'][selected]['ticker']}) 분석 차트", 
        template="plotly_white", 
        height=550,
        xaxis_range=[date_list[-view_days], date_list[-1]],
        hovermode="x unified"
    )
    st.plotly_chart(fig, use_container_width=True)
