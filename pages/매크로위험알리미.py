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

# 🎨 가독성 극대화 CSS (카드 내 줄바꿈 및 간격 강제 제어)
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700&display=swap');
html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; color: #111827 !important; }

/* 카드별 독립 공간 확보 */
.mini-card {
    border: 1px solid #e1e4e8;
    border-radius: 8px;
    padding: 8px;
    margin-bottom: 10px;
    background-color: #ffffff;
}
.buy-border { border-top: 5px solid #10b981; }
.wait-border { border-top: 5px solid #f59e0b; }
.sell-border { border-top: 5px solid #ef4444; }

.ticker-text { font-size: 0.85rem; font-weight: bold; color: #1f2937; }
.val-text { font-size: 0.75rem; color: #4b5563; }
.perc-text { font-size: 0.8rem; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

st.title("📊 매크로경제 위험알리미")
st.markdown("---")

# [3] 데이터 로딩
@st.cache_data(ttl=300)
def load_all_data():
    return get_all_market_data()

with st.spinner("⏳ JEFF 연구소 데이터 분석 중..."):
    all_data = load_all_data()
    df_sectors = calculate_sector_scores(all_data['sector_etfs'])
    df_individual = calculate_individual_metrics(all_data['individual_stocks'])
    df_core = calculate_core_sector_scores(all_data['core_sectors'])

# [4] 메인 시장 상태 (원본 문구 보존)
if not df_sectors.empty:
    m1, m2, m3 = st.columns(3)
    avg_l, avg_s = df_sectors['L-score'].mean(), df_sectors['S-score'].mean()
    m1.metric("평균 L-score", f"{avg_l:.2f}")
    m2.metric("평균 S-score", f"{avg_s:.2f}")
    with m3:
        if avg_l > 0 and avg_s > 0: st.success("✅ 매수 신호 (상승장)")
        elif avg_l < 0 and avg_s < 0: st.error("🚨 도망챠! (하락장)")
        else: st.warning("⚠️ 관망 (방향 탐색)")
    st.caption("💡 시장 상태 판별 기준: 전체 평균 장기/단기 스코어가 모두 0보다 크면 '매수', 모두 0보다 작으면 '도망챠!', 그 외는 '관망'입니다. 객관적인 숫자를 믿으십시오.")

st.markdown("---")

# [5] 메인 탭
tab1, tab2, tab3 = st.tabs(["📈 섹터 ETF", "💹 개별 종목", "🎯 핵심 11"])

with tab1:
    st.subheader("📈 섹터 ETF 분석")
    sub_t, sub_c = st.tabs(["📑 테이블 뷰", "🎴 카드 뷰"])
    
    with sub_t:
        st.dataframe(df_sectors.style.background_gradient(cmap='RdYlGn', subset=['L-score', 'S-score', 'S-L', '20일(%)'])
                     .format({'L-score': '{:.2f}', 'S-score': '{:.2f}', 'S-L': '{:.2f}', '20일(%)': '{:.2f}%'}),
                     use_container_width=True, height=450)

    with sub_c:
        # ⭐ [초록불 우선 정렬] 
        df_sorted = df_sectors.copy()
        def get_priority(row):
            if row['S-score'] > 0 and row['L-score'] > 0: return 0
            if row['S-score'] < 0 and row['L-score'] < 0: return 2
            return 1
        df_sorted['p'] = df_sorted.apply(get_priority, axis=1)
        df_sorted = df_sorted.sort_values(['p', 'S-L'], ascending=[True, False]).reset_index(drop=True)

        # 💡 [가독성 혁명] 한 줄에 3개씩, 각 정보를 분리해서 표시
        row_count = 3
        cols = st.columns(row_count)
        
        for idx, row in df_sorted.iterrows():
            with cols[idx % row_count]:
                sig_class = "buy-border" if row['p'] == 0 else ("sell-border" if row['p'] == 2 else "wait-border")
                sig_icon = "🟢" if row['p'] == 0 else ("🔴" if row['p'] == 2 else "🟡")
                
                # HTML을 사용하되 숫자가 섞이지 않도록 명확한 구조로 작성
                st.markdown(f"""
                <div class="mini-card {sig_class}">
                    <div class="ticker-text">{sig_icon} {row['섹터']}</div>
                    <div class="val-text">티커: <b>{row['티커']}</b></div>
                    <div class="val-text">S-L: {row['S-L']:.3f}</div>
                    <div class="perc-text" style="color:{'#10b981' if row['20일(%)'] > 0 else '#ef4444'}">
                        {row['20일(%)']}%
                    </div>
                </div>
                """, unsafe_allow_html=True)

    # ⭐ 원본 설명 문구 복구 100%
    st.markdown("##### 💡 퀀트 지표 핵심 요약")
    st.caption("**📊 L-score (장기 체력)**: 200일선 이격도, 52주 고점 위치 등을 종합한 장기 추세 점수입니다.")
    st.caption("**🚀 S-score (단기 기세)**: 20일선 이격도, 1개월 수익률 등을 종합한 단기 모멘텀 점수입니다.")
    st.caption("---")
    st.caption("1️⃣ **S-L (추세 가속도):** 단기 모멘텀(S)에서 장기 모멘텀(L)을 뺀 값입니다. 값이 클수록 최근 돈이 맹렬하게 몰리고 있음을 뜻합니다.")
    st.caption("2️⃣ **미너비니 절대 추세 필터 (랭킹 보정)**: 하락 추세 섹터는 가짜 신호로 간주하여 강등시켰습니다.")

# [6] 기타 탭
with tab2: st.dataframe(df_individual, use_container_width=True)
with tab3: st.dataframe(df_core, use_container_width=True)

# [7] 차트 (로컬 방어 로직)
st.markdown("---")
selected = st.selectbox("📊 상세 차트", list(all_data['sector_etfs'].keys()))
if selected:
    hist = all_data['sector_etfs'][selected]['history'].copy()
    if isinstance(hist.columns, pd.MultiIndex): hist.columns = hist.columns.get_level_values(0)
    date_list = hist.index.tolist()
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=date_list, y=hist['Close'].values.flatten(), name='종가', line=dict(color='blue', width=2)))
    fig.update_layout(title=f"{selected} 차트", template="plotly_white", height=450)
    st.plotly_chart(fig, use_container_width=True)
