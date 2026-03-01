import streamlit as st
import plotly.graph_objects as go
import sys
import os
import pandas as pd
import numpy as np

# [1] 🎨 디자인 스타일 설정 (글자색 시인성 강화 + 흰색 배제)
st.set_page_config(page_title="매크로 위험알리미", page_icon="📊", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; }
    .block-container { padding-top: 3.5rem !important; }

    /* ── 통합 카드 공통 스타일 ── */
    .unified-card {
        background: #ffffff;
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 12px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        display: flex;
        flex-direction: column;
        justify-content: center;
        min-height: 100px;
    }
    
    /* 🎨 신호별 스타일 (글자색 진하게 고정) */
    .card-buy  { border-left: 10px solid #10b981; background: #ecfdf5; color: #064e3b !important; } /* 매수신호: 진한 초록 */
    .card-wait { border-left: 10px solid #f59e0b; background: #fffbeb; color: #78350f !important; } /* 관망: 진한 갈색 */
    .card-exit { border-left: 10px solid #ef4444; background: #fef2f2; color: #7f1d1d !important; } /* 도망챠: 진한 빨강 */
    .card-rev  { border-left: 10px solid #8b5cf6; background: #f5f3ff; color: #4c1d95 !important; } /* 역발상: 진한 보라 */

    .ticker-label { font-size: 1.1rem; font-weight: 800; margin-bottom: 4px; display: block; }
    .signal-text { font-size: 0.9rem; font-weight: 700; margin-bottom: 6px; }
    .score-line { font-size: 0.85rem; border-top: 1px solid rgba(0,0,0,0.05); padding-top: 6px; margin-top: 4px; }
    
    @media (max-width: 640px) {
        .block-container { padding-top: 4rem !important; }
        .ticker-label { font-size: 0.95rem; }
        .signal-text { font-size: 0.8rem; }
    }
</style>
""", unsafe_allow_html=True)

# [2] 부품 및 데이터 로드 (기존 로직 유지)
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path: sys.path.append(parent_dir)

try:
    from data_fetcher import get_all_market_data
    from calculations import calculate_sector_scores, calculate_individual_metrics, calculate_core_sector_scores
except ImportError as e:
    st.error(f"🚨 부품 로딩 실패! (에러: {e})")
    st.stop()

@st.cache_data(ttl=300)
def load_all_data(): return get_all_market_data()

with st.spinner("⏳ 데이터를 분석 중입니다..."):
    all_data      = load_all_data()
    df_sectors    = calculate_sector_scores(all_data['sector_etfs'])
    df_individual = calculate_individual_metrics(all_data['individual_stocks'])
    df_core       = calculate_core_sector_scores(all_data['core_sectors'])

st.title("📊 매크로경제 위험알리미")
st.markdown("---")

# [3] 메인 시장 상태 지표
col1, col2, col3 = st.columns(3)
avg_l, avg_s = df_sectors['L-score'].mean(), df_sectors['S-score'].mean()
with col1: st.metric("평균 L-score", f"{avg_l:.2f}")
with col2: st.metric("평균 S-score", f"{avg_s:.2f}")
with col3:
    if avg_l > 0 and avg_s > 0: st.success("🟢 매수 신호 (상승장)")
    elif avg_l < 0 and avg_s < 0: st.error("🔴 도망챠! (하락장)")
    else: st.warning("🟡 관망 (방향 탐색)")

# [4] 메인 탭
tab1, tab2, tab3 = st.tabs(["📈 섹터 ETF", "💹 개별 종목", "🎯 11개 핵심 섹터"])

# ─────── TAB 1: 섹터 ETF (디자인 교체 완료) ───────
with tab1:
    st.subheader("📈 섹터 ETF 카드 뷰")
    cols = st.columns(2)
    # 신호 판정 루프
    for i, row in df_sectors.iterrows():
        l, s = row['L-score'], row['S-score']
        if l > 0 and s > 0:
            css, sig_txt, icon = "card-buy", "🟢 매수 신호", "✅"
        elif l < 0 and s < 0:
            css, sig_txt, icon = "card-exit", "🔴 도망챠!", "🚨"
        else:
            css, sig_txt, icon = "card-wait", "🟡 관망", "⚠️"
        
        with cols[i % 2]:
            st.markdown(f"""
            <div class="unified-card {css}">
                <div class="ticker-label">{icon} {row['섹터']} ({row['티커']})</div>
                <div class="signal-text">{sig_txt}</div>
                <div class="score-line">S-L: <b>{row['S-L']:.3f}</b> | 20일: <b>{row['20일(%)']:.2f}%</b></div>
            </div>""", unsafe_allow_html=True)

# ─────── TAB 2: 개별 종목 (디자인 교체 완료) ───────
with tab2:
    st.subheader("💹 개별 종목 카드 뷰")
    cols2 = st.columns(2)
    for i, row in df_individual.iterrows():
        ytd = row['연초대비']
        css = "card-buy" if ytd > 0 else "card-exit"
        sig_txt = "🟢 매수세 유지" if ytd > 0 else "🔴 하락 압력"
        icon = "📈" if ytd > 0 else "📉"
        
        with cols2[i % 2]:
            st.markdown(f"""
            <div class="unified-card {css}">
                <div class="ticker-label">{icon} {row['티커']} | ${row['현재가']:,.2f}</div>
                <div class="signal-text">{sig_txt} (YTD: {ytd:+.1f}%)</div>
                <div class="score-line">200일선: <b>{row['200대비']:+.1f}%</b> | 고점대비: <b>{row['high대비']:+.1f}%</b></div>
            </div>""", unsafe_allow_html=True)

# ─────── TAB 3: 11개 핵심 섹터 (디자인 교체 완료) ───────
with tab3:
    st.subheader("🎯 11개 핵심 섹터 카드 뷰")
    df_core_sorted = df_core.sort_values('S-SCORE', ascending=False).reset_index(drop=True)
    cols3 = st.columns(2)
    for i, row in df_core_sorted.iterrows():
        sc = float(row['S-SCORE'])
        if sc > 0.05:
            css, sig_txt, icon = "card-buy", "🟢 매수 우위", "🔥"
        elif sc < -0.05:
            css, sig_txt, icon = "card-exit", "🔴 도망챠!", "❄️"
        else:
            css, sig_txt, icon = "card-wait", "🟡 관망", "😐"
            
        with cols3[i % 2]:
            st.markdown(f"""
            <div class="unified-card {css}">
                <div class="ticker-label">{icon} {row['섹터']} ({row['티커']})</div>
                <div class="signal-text">{sig_txt}</div>
                <div class="score-line">S-SCORE: <b>{sc:+.3f}</b> | 20일 수익: <b>{row['20일(%)']:.2f}%</b></div>
            </div>""", unsafe_allow_html=True)

st.markdown("---")
st.caption("📊 JEFF의 퀀트 매크로 연구소 · S24+ 모바일 최적화 버전")
