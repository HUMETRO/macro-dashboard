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

# 🎨 [혁신] 모바일 4열 강제 고정 및 가독성 CSS
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700&display=swap');
html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; }

/* 💡 카드 컨테이너: 가로로 꽉 채우고 줄바꿈 허용 */
.card-container {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    justify-content: flex-start;
}

/* 💡 카드 개별 스타일: 모바일에서 강제로 약 23% 너비 차지 (한 줄에 4개) */
.metric-card {
    flex: 0 0 calc(25% - 6px);
    background-color: #ffffff;
    border-radius: 6px;
    padding: 6px;
    border: 1px solid #e5e7eb;
    box-sizing: border-box;
    min-height: 80px;
    text-align: center;
}

@media (max-width: 600px) {
    .metric-card {
        flex: 0 0 calc(33.33% - 6px); /* 💡 아주 작은 화면에선 3개씩 보이게 자동 조절 */
    }
}

.buy-signal  { border-top: 4px solid #10b981; background-color: #f0fdf4; }
.sell-signal { border-top: 4px solid #ef4444; background-color: #fef2f2; }
.wait-signal { border-top: 4px solid #f59e0b; background-color: #fffbeb; }

.ticker-header { font-size: 0.7rem; font-weight: 700; color: #111827 !important; margin-bottom: 2px; overflow: hidden; white-space: nowrap; }
.score-box     { font-size: 0.65rem; color: #374151 !important; line-height: 1.2; }
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
        if avg_l > 0 and avg_s > 0: st.success("✅ 매수 신호")
        elif avg_l < 0 and avg_s < 0: st.error("🚨 도망챠!")
        else: st.warning("⚠️ 관망")
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
        # ⭐ [초록불 우선 정렬 로직 고도화]
        df_sorted = df_sectors.copy()
        def get_priority(row):
            if row['S-score'] > 0 and row['L-score'] > 0: return 0  # 1순위: 초록
            if row['S-score'] < 0 and row['L-score'] < 0: return 2  # 3순위: 빨강
            return 1 # 2순위: 노랑
        df_sorted['p'] = df_sorted.apply(get_priority, axis=1)
        # 우선순위(p) 오름차순, S-L 내림차순 정렬
        df_sorted = df_sorted.sort_values(['p', 'S-L'], ascending=[True, False])

        # 💡 [강력 가시성] HTML 직접 주입 방식으로 4열 배치 구현
        cards_html = '<div class="card-container">'
        for _, row in df_sorted.iterrows():
            sig = "buy-signal" if row['S-score'] > 0 and row['L-score'] > 0 else \
                  "sell-signal" if row['S-score'] < 0 and row['L-score'] < 0 else "wait-signal"
            icon = "✅" if sig == "buy-signal" else ("🚨" if sig == "sell-signal" else "⚠️")
            
            cards_html += f"""
            <div class="metric-card {sig}">
                <div class="ticker-header">{icon} {row['섹터']}</div>
                <div class="score-box">
                    <b>{row['티커']}</b><br>
                    S-L: {row['S-L']}<br>
                    <b>{row['20일(%)']}%</b>
                </div>
            </div>
            """
        cards_html += '</div>'
        st.markdown(cards_html, unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

    # ⭐ 원본 설명 문구 복구 100%
    st.markdown("##### 💡 퀀트 지표 핵심 요약")
    st.caption("**📊 L-score (장기 체력)**: 200일선 이격도, 52주 고점 위치 등을 종합한 장기 추세 점수입니다.")
    st.caption("**🚀 S-score (단기 기세)**: 20일선 이격도, 1개월 수익률 등을 종합한 단기 모멘텀 점수입니다.")
    st.caption("---")
    st.caption("1️⃣ **S-L (추세 가속도):** 단기 모멘텀(S)에서 장기 모멘텀(L)을 뺀 값입니다. 값이 클수록 최근 돈이 맹렬하게 몰리고 있음을 뜻합니다.")
    st.caption("2️⃣ **미너비니 절대 추세 필터 (랭킹 보정)**: 하락 추세 섹터는 가짜 신호로 간주하여 강등시켰습니다.")

# [6] 기타 탭 및 차트 (정상 작동 로직 유지)
with tab2: st.dataframe(df_individual, use_container_width=True)
with tab3: st.dataframe(df_core, use_container_width=True)

st.markdown("---")
selected = st.selectbox("📊 상세 차트", list(all_data['sector_etfs'].keys()))
if selected:
    hist = all_data['sector_etfs'][selected]['history'].copy()
    if isinstance(hist.columns, pd.MultiIndex): hist.columns = hist.columns.get_level_values(0)
    date_list = hist.index.tolist()
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=date_list, y=hist['Close'].values.flatten(), name='종가', line=dict(color='blue')))
    fig.update_layout(title=f"{selected} 차트", template="plotly_white", height=400)
    st.plotly_chart(fig, use_container_width=True)
