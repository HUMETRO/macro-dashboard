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

# 🎨 카드 가독성 극대화 CSS (글자 선명도 강화)
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700&display=swap');
html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; }

.metric-card {
    background-color: #ffffff;
    border-radius: 8px;
    padding: 10px;
    border: 1px solid #e5e7eb;
    margin-bottom: 5px;
    min-height: 95px;
}
.buy-signal  { border-left: 5px solid #10b981; background-color: #f0fdf4; }
.sell-signal { border-left: 5px solid #ef4444; background-color: #fef2f2; }
.wait-signal { border-left: 5px solid #f59e0b; background-color: #fffbeb; }

/* 💡 글씨 색상을 짙은 회색으로 고정하여 가독성 확보 */
.ticker-header { font-size: 0.82rem; font-weight: 700; color: #111827 !important; margin-bottom: 2px; }
.score-box     { font-size: 0.72rem; color: #374151 !important; line-height: 1.4; }
</style>
""", unsafe_allow_html=True)

st.title("📊 매크로경제 위험알리미")
st.markdown("---")

# [3] 데이터 로딩
@st.cache_data(ttl=300)
def load_all_data():
    return get_all_market_data()

with st.spinner("⏳ JEFF 연구소 데이터를 분석 중..."):
    all_data = load_all_data()
    df_sectors = calculate_sector_scores(all_data['sector_etfs'])
    df_individual = calculate_individual_metrics(all_data['individual_stocks'])
    df_core = calculate_core_sector_scores(all_data['core_sectors'])

# [4] 메인 시장 상태 지표 (원본 문구 보존)
if not df_sectors.empty and 'L-score' in df_sectors.columns:
    col1, col2, col3 = st.columns(3)
    avg_l = df_sectors['L-score'].mean()
    avg_s = df_sectors['S-score'].mean()
    with col1: st.metric("평균 L-score", f"{avg_l:.2f}", delta="장기 체력", delta_color="off")
    with col2: st.metric("평균 S-score", f"{avg_s:.2f}", delta="단기 기세", delta_color="off")
    with col3:
        if avg_l > 0 and avg_s > 0: st.success("✅ 매수 신호 (상승장)")
        elif avg_l < 0 and avg_s < 0: st.error("🚨 도망챠! (하락장)")
        else: st.warning("⚠️ 관망 (방향 탐색)")
    st.caption("💡 시장 상태 판별 기준: 전체 평균 장기/단기 스코어가 모두 0보다 크면 '매수', 모두 0보다 작으면 '도망챠!', 그 외는 '관망'입니다. 객관적인 숫자를 믿으십시오.")

# [5] 조기경보 시스템 (원본 문구 보존)
top_5_sectors = df_sectors.head(5)['섹터'].tolist()
safe_assets = ['CASH', '장기국채', '물가연동채', '유틸리티', '필수소비재']
safe_count = sum(1 for sector in top_5_sectors if sector in safe_assets)
if safe_count >= 2:
    st.error(f"🚨 **안전자산 쏠림 경보 발령!** 현재 상위 5개 섹터 중 {safe_count}개가 방어적 자산입니다. 시장의 스마트머니가 위험을 피해 피난하고 있습니다. 주식 비중 확대를 멈추고 관망하십시오!")

st.markdown("---")

# [6] 메인 탭 구성
tab1, tab2, tab3 = st.tabs(["📈 섹터 ETF", "💹 개별 종목", "🎯 11개 핵심 섹터"])

with tab1:
    st.subheader("📈 섹터 ETF 스코어 (S-L 순위)")
    sub_t, sub_c = st.tabs(["📑 테이블 뷰", "🎴 카드 뷰"])
    
    with sub_t:
        st.dataframe(df_sectors.style.background_gradient(cmap='RdYlGn', subset=['L-score', 'S-score', 'S-L', '20일(%)'])
                     .format({'L-score': '{:.2f}', 'S-score': '{:.2f}', 'S-L': '{:.2f}', '20일(%)': '{:.2f}%'}),
                     use_container_width=True, height=450)

    with sub_c:
        # ⭐ 소장님 요청: [초록불 우선 정렬] 
        # 매수신호(1순위) -> 관망(2순위) -> 매도신호(3순위) 순으로 정렬
        df_sorted = df_sectors.copy()
        df_sorted['priority'] = df_sorted.apply(lambda x: 1 if x['S-score'] > 0 and x['L-score'] > 0 else (3 if x['S-score'] < 0 and x['L-score'] < 0 else 2), axis=1)
        df_sorted = df_sorted.sort_values(['priority', 'S-L'], ascending=[True, False]).reset_index(drop=True)

        # ⭐ 소장님 요청: [모바일 4열 배치]
        cols = st.columns(4) 
        for idx, row in df_sorted.iterrows():
            with cols[idx % 4]:
                sig = "buy-signal" if row['S-score'] > 0 and row['L-score'] > 0 else \
                      "sell-signal" if row['S-score'] < 0 and row['L-score'] < 0 else "wait-signal"
                icon = "✅" if sig == "buy-signal" else ("🚨" if sig == "sell-signal" else "⚠️")
                st.markdown(f"""
                <div class="metric-card {sig}">
                    <div class="ticker-header">{icon} {row['섹터']} ({row['티커']})</div>
                    <div class="score-box">
                        <b>S-L: {row['S-L']}</b> | <b>{row['20일(%)']}%</b><br>
                        L:{row['L-score']} / S:{row['S-score']}
                    </div>
                </div>
                """, unsafe_allow_html=True)

    # ⭐ 원본 설명 문구 복구 100%
    st.markdown("##### 💡 퀀트 지표 핵심 요약")
    st.caption("**📊 L-score (장기 체력)**: 200일선 이격도, 52주 고점 위치 등을 종합한 장기 추세 점수입니다.")
    st.caption("**🚀 S-score (단기 기세)**: 20일선 이격도, 1개월 수익률 등을 종합한 단기 모멘텀 점수입니다.")
    st.caption("---")
    st.caption("1️⃣ **S-L (추세 가속도):** 단기 모멘텀(S)에서 장기 모멘텀(L)을 뺀 값입니다. 값이 클수록 최근 돈이 맹렬하게 몰리고 있음을 뜻합니다.")
    st.caption("2️⃣ **미너비니 절대 추세 필터 (랭킹 보정)**: 하락 추세 섹터는 가짜 신호로 간주하여 강제 강등시켰습니다.")

# [7] 기타 테이블 및 차트 (기존 로직 유지)
with tab2:
    st.dataframe(df_individual.style.background_gradient(cmap='RdYlGn', subset=['연초대비', 'high대비', '200대비', '52저대비']), use_container_width=True, height=450)
with tab3:
    st.dataframe(df_core.style.background_gradient(cmap='RdYlGn', subset=['S-SCORE', '20일(%)']), use_container_width=True, height=450)

# [8] 상세 차트 (MultiIndex/날짜 완벽 대응)
st.markdown("---")
selected = st.selectbox("📊 상세 분석 차트 선택", list(all_data['sector_etfs'].keys()))
if selected:
    hist = all_data['sector_etfs'][selected]['history'].copy()
    if isinstance(hist.columns, pd.MultiIndex): hist.columns = hist.columns.get_level_values(0)
    date_list = hist.index.tolist()
    def gv(s): return s.values.flatten() if isinstance(s, pd.DataFrame) else s.values

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=date_list, y=gv(hist['Close']), name='종가', line=dict(color='blue', width=2)))
    if 'MA200' in hist.columns: fig.add_trace(go.Scatter(x=date_list, y=gv(hist['MA200']), name='MA200', line=dict(dash='dot', color='green', width=2)))
    fig.update_layout(title=f"{selected} 차트", template="plotly_white", height=450, xaxis_range=[date_list[-500], date_list[-1]])
    st.plotly_chart(fig, use_container_width=True)
