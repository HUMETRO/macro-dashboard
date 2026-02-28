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

# 🎨 [블랙 테마 & 모바일 4열 고정 CSS]
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700&display=swap');
html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; background-color: #0e1117; color: #ffffff; }

/* 카드 컨테이너: 가로 배치 강제 */
.card-wrapper {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    justify-content: flex-start;
}

/* 개별 카드: 모바일 3~4열, PC 6열 이상 */
.quant-card {
    flex: 0 0 calc(25% - 8px); /* 모바일 기본 4열 */
    background-color: #1e2128;
    border-radius: 8px;
    padding: 10px;
    border: 1px solid #30363d;
    text-align: center;
    min-height: 100px;
}

@media (max-width: 600px) {
    .quant-card {
        flex: 0 0 calc(33.33% - 8px); /* 작은 화면 3열 */
        padding: 6px;
    }
}

/* 신호별 색상 테두리 */
.buy-border { border-top: 4px solid #10b981 !important; }
.wait-border { border-top: 4px solid #f59e0b !important; }
.sell-border { border-top: 4px solid #ef4444 !important; }

.ticker-name { font-size: 0.8rem; font-weight: 700; color: #ffffff; margin-bottom: 2px; }
.ticker-sub { font-size: 0.65rem; color: #8b949e; }
.value-box { font-size: 0.75rem; font-weight: 600; margin-top: 4px; }
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
        st.dataframe(df_sectors, use_container_width=True, height=450)

    with tab1:
        with sub_c:
            # ⭐ [정렬 로직 강화] 초록불이 무조건 최상단
            df_sorted = df_sectors.copy()
            df_sorted['p'] = df_sorted.apply(lambda r: 0 if r['S-score']>0 and r['L-score']>0 else (2 if r['S-score']<0 and r['L-score']<0 else 1), axis=1)
            df_sorted = df_sorted.sort_values(['p', 'S-L'], ascending=[True, False]).reset_index(drop=True)

            # 💡 [강력 배치] HTML Flexbox로 모바일 강제 정렬
            card_html = '<div class="card-wrapper">'
            for _, row in df_sorted.iterrows():
                cls = "buy-border" if row['p'] == 0 else ("sell-border" if row['p'] == 2 else "wait-border")
                ico = "✅" if row['p'] == 0 else ("🚨" if row['p'] == 2 else "⚠️")
                color = "#10b981" if row['20일(%)'] > 0 else "#ef4444"
                
                card_html += f"""
                <div class="quant-card {cls}">
                    <div class="ticker-name">{ico} {row['섹터']}</div>
                    <div class="ticker-sub">{row['티커']}</div>
                    <div class="value-box">S-L: {row['S-L']:.2f}</div>
                    <div class="value-box" style="color:{color}">{row['20일(%)']}%</div>
                </div>
                """
            card_html += '</div>'
            st.markdown(card_html, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("##### 💡 퀀트 지표 핵심 요약")
    st.caption("1️⃣ **S-L (추세 가속도):** 값이 클수록 최근 돈이 맹렬하게 몰림")
    st.caption("2️⃣ **미너비니 필터:** 하락 추세 섹터는 강제 강등")

# [6] 기타 탭 및 차트 (기존 로직 유지)
with tab2: st.dataframe(df_individual, use_container_width=True)
with tab3: st.dataframe(df_core, use_container_width=True)

st.markdown("---")
selected = st.selectbox("📊 상세 차트", list(all_data['sector_etfs'].keys()))
if selected:
    hist = all_data['sector_etfs'][selected]['history'].copy()
    if isinstance(hist.columns, pd.MultiIndex): hist.columns = hist.columns.get_level_values(0)
    fig = go.Figure(data=[go.Scatter(x=hist.index, y=hist['Close'].values.flatten(), name='Price')])
    fig.update_layout(template="plotly_dark", height=450) # 차트도 다크 테마 적용
    st.plotly_chart(fig, use_container_width=True)
