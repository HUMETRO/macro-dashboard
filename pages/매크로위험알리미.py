import streamlit as st
import plotly.graph_objects as go
import sys
import os
import pandas as pd
import numpy as np

# [1] 경로 및 부품 로드 (원본 유지)
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

try:
    from data_fetcher import get_all_market_data
    from calculations import calculate_sector_scores, calculate_individual_metrics, calculate_core_sector_scores
except ImportError as e:
    st.error(f"🚨 부품 로딩 실패! (에러: {e})")
    st.stop()

st.set_page_config(page_title="매크로 위험알리미", page_icon="📊", layout="wide")

# [2] 🎨 100% 보장되는 고대비 카드 스타일 (흰색 글씨 영구 퇴출)
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700&display=swap');
html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; }
.block-container { padding-top: 3.5rem !important; }

/* ── 통합 카드 디자인 ── */
.unified-card {
    background: #ffffff;
    border-radius: 12px;
    padding: 18px;
    margin-bottom: 12px;
    border: 1px solid #e2e8f0;
    box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    display: flex;
    flex-direction: column;
    justify-content: center;
    min-height: 110px;
}

/* 🎨 신호별 포인트 컬러 (글자색 진하게 고정) */
.card-buy  { border-left: 10px solid #10b981; background: #ecfdf5; color: #064e3b !important; } 
.card-wait { border-left: 10px solid #f59e0b; background: #fffbeb; color: #78350f !important; } 
.card-exit { border-left: 10px solid #ef4444; background: #fef2f2; color: #7f1d1d !important; } 

.ticker-label { font-size: 1.15rem; font-weight: 800; margin-bottom: 4px; }
.signal-text  { font-size: 0.95rem; font-weight: 700; margin-bottom: 6px; }
.score-line   { font-size: 0.85rem; border-top: 1px solid rgba(0,0,0,0.1); padding-top: 6px; margin-top: 4px; }

@media (max-width: 640px) {
    .block-container { padding-top: 4rem !important; }
    h1 { font-size: 1.2rem !important; }
}
</style>
""", unsafe_allow_html=True)

st.title("📊 매크로경제 위험알리미")
st.markdown("---")

# [3] 데이터 로딩
@st.cache_data(ttl=300)
def load_all_data():
    return get_all_market_data()

with st.spinner("⏳ 데이터를 분석 중입니다..."):
    all_data      = load_all_data()
    df_sectors    = calculate_sector_scores(all_data['sector_etfs'])
    df_individual = calculate_individual_metrics(all_data['individual_stocks'])
    df_core       = calculate_core_sector_scores(all_data['core_sectors'])

# [4] 상단 지표 (원본 보존)
if not df_sectors.empty and 'L-score' in df_sectors.columns:
    col1, col2, col3 = st.columns(3)
    avg_l, avg_s = df_sectors['L-score'].mean(), df_sectors['S-score'].mean()
    with col1: st.metric("평균 L-score", f"{avg_l:.2f}")
    with col2: st.metric("평균 S-score", f"{avg_s:.2f}")
    with col3:
        if avg_l > 0 and avg_s > 0: st.success("✅ 매수 신호 (상승장)")
        elif avg_l < 0 and avg_s < 0: st.error("🚨 도망챠! (하락장)")
        else: st.warning("⚠️ 관망 (방향 탐색)")

# [5] 메인 탭
tab1, tab2, tab3 = st.tabs(["📈 섹터 ETF", "💹 개별 종목", "🎯 11개 핵심 섹터"])

# ─────── TAB1: 섹터 ETF ───────
with tab1:
    sub_t, sub_c = st.tabs(["📑 테이블 뷰", "🎴 카드 뷰"])
    with sub_t: # 테이블 뷰 보존
        st.dataframe(df_sectors.style.background_gradient(cmap='RdYlGn', subset=['L-score','S-score','S-L','20일(%)']), use_container_width=True, height=450)
    with sub_c: # 카드 뷰 복구
        cols = st.columns(2)
        for i, row in df_sectors.iterrows():
            l, s = row['L-score'], row['S-score']
            css, sig, icon = ("card-buy", "✅ 매수 신호", "🟢") if l > 0 and s > 0 else (("card-exit", "🚨 도망챠!", "🔴") if l < 0 and s < 0 else ("card-wait", "⚠️ 관망", "🟡"))
            with cols[i % 2]:
                st.markdown(f"""
                <div class="unified-card {css}">
                    <div class="ticker-label">{icon} {row['섹터']} ({row['티커']})</div>
                    <div class="signal-text">{sig}</div>
                    <div class="score-line">S-L: <b>{row['S-L']:.3f}</b> | 20일: <b>{row['20일(%)']:.2f}%</b></div>
                </div>""", unsafe_allow_html=True)

# ─────── TAB2: 개별 종목 ───────
with tab2:
    sub_t2, sub_c2 = st.tabs(["📑 테이블 뷰", "🎴 카드 뷰"])
    with sub_t2: # 테이블 뷰 보존
        st.dataframe(df_individual.style.background_gradient(cmap='RdYlGn', subset=['연초대비','200대비']), use_container_width=True, height=450)
    with sub_c2: # 카드 뷰 복구
        cols2 = st.columns(2)
        for i, row in df_individual.iterrows():
            ytd = row.get('연초대비', 0)
            css, sig, icon = ("card-buy", "✅ 매수 신호", "🟢") if ytd > 0 else ("card-exit", "🚨 도망챠!", "🔴")
            with cols2[i % 2]:
                st.markdown(f"""
                <div class="unified-card {css}">
                    <div class="ticker-label">{icon} {row['티커']} | ${row['현재가']:,.2f}</div>
                    <div class="signal-text">{sig} (YTD: {ytd:+.1f}%)</div>
                    <div class="score-line">200일: <b>{row['200대비']:+.1f}%</b> | 고점대비: <b>{row['high대비']:+.1f}%</b></div>
                </div>""", unsafe_allow_html=True)

# ─────── TAB3: 11개 핵심 섹터 ───────
with tab3:
    sub_t3, sub_c3 = st.tabs(["📑 테이블 뷰", "🎴 카드 뷰"])
    with sub_t3: # 테이블 뷰 보존
        st.dataframe(df_core.style.background_gradient(cmap='RdYlGn', subset=['S-SCORE']), use_container_width=True, height=450)
    with sub_c3: # 카드 뷰 복구
        df_core_sorted = df_core.sort_values('S-SCORE', ascending=False).reset_index(drop=True)
        cols3 = st.columns(2)
        for i, row in df_core_sorted.iterrows():
            sc = float(row['S-SCORE'])
            css, sig, icon = ("card-buy", "✅ 매수 신호", "🟢") if sc > 0.05 else (("card-exit", "🚨 도망챠!", "🔴") if sc < -0.05 else ("card-wait", "⚠️ 관망", "🟡"))
            with cols3[i % 2]:
                st.markdown(f"""
                <div class="unified-card {css}">
                    <div class="ticker-label">{icon} #{i+1} {row['섹터']} ({row['티커']})</div>
                    <div class="signal-text">{sig}</div>
                    <div class="score-line">S: <b>{sc:+.3f}</b> | 20일 수익: <b>{row['20일(%)']:.2f}%</b></div>
                </div>""", unsafe_allow_html=True)

# [7] 상세 차트 (원본 보존)
st.markdown("---")
selected = st.selectbox("📉 상세 분석 차트 선택", list(all_data['sector_etfs'].keys()))
if selected:
    hist = all_data['sector_etfs'][selected]['history'].copy()
    if isinstance(hist.columns, pd.MultiIndex): hist.columns = hist.columns.get_level_values(0)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=hist.index, y=hist['Close'].values.flatten(), name='종가', line=dict(color='blue')))
    st.plotly_chart(fig.update_layout(title=f"{selected} 분석 차트", template="plotly_white"), use_container_width=True)
