import streamlit as st
import plotly.graph_objects as go
import sys
import os
import pandas as pd
import numpy as np

# [1] 🎨 통합 카드 스타일 (글자색 시인성 강화)
st.set_page_config(page_title="매크로 위험알리미", page_icon="📊", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; }
    .block-container { padding-top: 3.5rem !important; }

    /* ── 소장님 전용 통합 카드 ── */
    .unified-card {
        background: #ffffff; border-radius: 12px; padding: 16px; margin-bottom: 12px;
        border: 1px solid #e2e8f0; box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        display: flex; flex-direction: column; justify-content: center; min-height: 100px;
    }
    .card-buy  { border-left: 10px solid #10b981; background: #ecfdf5; color: #064e3b !important; } 
    .card-wait { border-left: 10px solid #f59e0b; background: #fffbeb; color: #78350f !important; } 
    .card-exit { border-left: 10px solid #ef4444; background: #fef2f2; color: #7f1d1d !important; } 

    .ticker-label { font-size: 1.1rem; font-weight: 800; margin-bottom: 4px; display: block; }
    .signal-text { font-size: 0.9rem; font-weight: 700; margin-bottom: 6px; }
    .score-line { font-size: 0.85rem; border-top: 1px solid rgba(0,0,0,0.1); padding-top: 6px; margin-top: 4px; }
</style>
""", unsafe_allow_html=True)

# [2] 경로 및 부품 로드 (원본 유지)
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path: sys.path.append(parent_dir)

try:
    from data_fetcher import get_all_market_data
    from calculations import calculate_sector_scores, calculate_individual_metrics, calculate_core_sector_scores
except ImportError as e:
    st.error(f"🚨 부품 로딩 실패! {e}"); st.stop()

@st.cache_data(ttl=300)
def load_all_data(): return get_all_market_data()

with st.spinner("⏳ 분석 중..."):
    all_data = load_all_data()
    df_sectors = calculate_sector_scores(all_data['sector_etfs'])
    df_individual = calculate_individual_metrics(all_data['individual_stocks'])
    df_core = calculate_core_sector_scores(all_data['core_sectors'])

st.title("📊 매크로경제 위험알리미")
st.markdown("---")

# [3] 시장 상태 메트릭 (원본 보존)
col1, col2, col3 = st.columns(3)
avg_l, avg_s = df_sectors['L-score'].mean(), df_sectors['S-score'].mean()
with col1: st.metric("평균 L-score", f"{avg_l:.2f}")
with col2: st.metric("평균 S-score", f"{avg_s:.2f}")
with col3:
    if avg_l > 0 and avg_s > 0: st.success("✅ 매수 신호 (상승장)")
    elif avg_l < 0 and avg_s < 0: st.error("🚨 도망챠! (하락장)")
    else: st.warning("⚠️ 관망 (방향 탐색)")

# [4] 메인 탭 구성
tab1, tab2, tab3 = st.tabs(["📈 섹터 ETF", "💹 개별 종목", "🎯 11개 핵심 섹터"])

# ─────── TAB 1: 섹터 ETF ───────
with tab1:
    sub_t, sub_c = st.tabs(["📑 테이블 뷰", "🎴 카드 뷰"])
    with sub_t: # 기존 테이블 뷰 보존
        st.dataframe(df_sectors.style.background_gradient(cmap='RdYlGn', subset=['L-score','S-score','S-L','20일(%)']), use_container_width=True)
    with sub_c: # 신규 카드 뷰 이식
        cols = st.columns(2)
        for i, row in df_sectors.iterrows():
            l, s = row['L-score'], row['S-score']
            css, sig, icon = ("card-buy", "🟢 매수 신호", "✅") if l > 0 and s > 0 else (("card-exit", "🔴 도망챠!", "🚨") if l < 0 and s < 0 else ("card-wait", "🟡 관망", "⚠️"))
            with cols[i % 2]:
                st.markdown(f'<div class="unified-card {css}"><div class="ticker-label">{icon} {row["섹터"]}</div><div class="signal-text">{sig}</div><div class="score-line">S-L: {row["S-L"]:.3f} | 20일: {row["20일(%)"]:.2f}%</div></div>', unsafe_allow_html=True)

# ─────── TAB 2: 개별 종목 ───────
with tab2:
    sub_t2, sub_c2 = st.tabs(["📑 테이블 뷰", "🎴 카드 뷰"])
    with sub_t2: # 기존 테이블 뷰 보존
        st.dataframe(df_individual.style.background_gradient(cmap='RdYlGn', subset=['연초대비','200대비']), use_container_width=True)
    with sub_c2: # 신규 카드 뷰 이식
        cols2 = st.columns(2)
        for i, row in df_individual.iterrows():
            ytd = row['연초대비']
            css, sig, icon = ("card-buy", "🟢 매수 우위", "📈") if ytd > 0 else ("card-exit", "🔴 하락 압력", "📉")
            with cols2[i % 2]:
                st.markdown(f'<div class="unified-card {css}"><div class="ticker-label">{icon} {row["티커"]} | ${row["현재가"]:,.2f}</div><div class="signal-text">{sig} (YTD: {ytd:+.1f}%)</div><div class="score-line">200일선: {row["200대비"]:+.1f}% | 고점대비: {row["high대비"]:+.1f}%</div></div>', unsafe_allow_html=True)

# ─────── TAB 3: 핵심 섹터 ───────
with tab3:
    sub_t3, sub_c3 = st.tabs(["📑 테이블 뷰", "🎴 카드 뷰"])
    with sub_t3: # 기존 테이블 뷰 보존
        st.dataframe(df_core.style.background_gradient(cmap='RdYlGn', subset=['S-SCORE']), use_container_width=True)
    with sub_c3: # 신규 카드 뷰 이식
        cols3 = st.columns(2)
        df_core_sorted = df_core.sort_values('S-SCORE', ascending=False).reset_index(drop=True)
        for i, row in df_core_sorted.iterrows():
            sc = float(row['S-SCORE'])
            css, sig, icon = ("card-buy", "🟢 매수 우위", "🔥") if sc > 0.05 else (("card-exit", "🔴 도망챠!", "❄️") if sc < -0.05 else ("card-wait", "🟡 관망", "😐"))
            with cols3[i % 2]:
                st.markdown(f'<div class="unified-card {css}"><div class="ticker-label">{icon} {row["섹터"]}</div><div class="signal-text">{sig}</div><div class="score-line">S-SCORE: {sc:+.3f} | 20일: {row["20일(%)"]:.2f}%</div></div>', unsafe_allow_html=True)

# [5] 차트 분석 섹션 (완벽 보존)
st.markdown("---")
selected = st.selectbox("📉 상세 분석 차트 선택", list(all_data['sector_etfs'].keys()))
if selected:
    hist = all_data['sector_etfs'][selected]['history'].copy()
    if isinstance(hist.columns, pd.MultiIndex): hist.columns = hist.columns.get_level_values(0)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=hist.index, y=hist['Close'].values.flatten(), name='종가', line=dict(color='blue')))
    if 'MA200' in hist.columns: fig.add_trace(go.Scatter(x=hist.index, y=hist['MA200'].values.flatten(), name='MA200', line=dict(dash='dot', color='green')))
    st.plotly_chart(fig.update_layout(title=f"{selected} 분석 차트", template="plotly_white"), use_container_width=True)
