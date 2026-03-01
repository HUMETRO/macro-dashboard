import streamlit as st
import plotly.graph_objects as go
import sys
import os
import pandas as pd
import numpy as np

# [1] 경로 및 부품 로드 (소장님 원본 100% 유지)
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

# [2] 스타일 설정 (순정 디자인 + 흰색 글씨만 시인성 강화)
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700&display=swap');
html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; }
.block-container { padding-top: 3.5rem !important; }

/* 섹터/개별/핵심 카드 (원본 스타일 보존, 글자색만 진하게) */
.metric-card, .stock-card, .core-card {
    background: #fff; border-radius: 8px; padding: 10px; border: 1px solid #e5e7eb; margin-bottom: 8px;
    color: #1e293b !important;
}
.buy-signal, .stock-up, .core-strong { border-left: 5px solid #10b981; background: #f0fdf4; }
.sell-signal, .stock-down, .core-weak { border-left: 5px solid #ef4444; background: #fef2f2; }
.wait-signal, .stock-flat, .core-mid { border-left: 5px solid #f59e0b; background: #fffbeb; }

.ticker-header, .stock-name, .core-name { font-size: 0.85rem; font-weight: 700; color: #111827 !important; }
.score-box, .stock-meta, .core-meta { font-size: 0.75rem; color: #374151 !important; line-height: 1.5; }

@media (max-width: 640px) {
    .block-container { padding-top: 4rem !important; }
    h1 { font-size: 1.2rem !important; }
}
</style>
""", unsafe_allow_html=True)

st.title("📊 매크로경제 위험알리미")
st.markdown("---")

# [3] 데이터 로딩 (순정 로직)
@st.cache_data(ttl=300)
def load_all_data():
    return get_all_market_data()

with st.spinner("⏳ 데이터를 분석 중입니다..."):
    all_data      = load_all_data()
    df_sectors    = calculate_sector_scores(all_data['sector_etfs'])
    df_individual = calculate_individual_metrics(all_data['individual_stocks'])
    df_core       = calculate_core_sector_scores(all_data['core_sectors'])

# [4] 시장 지표 및 조기경보 (원본 보존)
if not df_sectors.empty and 'L-score' in df_sectors.columns:
    col1, col2, col3 = st.columns(3)
    avg_l, avg_s = df_sectors['L-score'].mean(), df_sectors['S-score'].mean()
    with col1: st.metric("평균 L-score", f"{avg_l:.2f}", delta="장기 체력", delta_color="off")
    with col2: st.metric("평균 S-score", f"{avg_s:.2f}", delta="단기 기세", delta_color="off")
    with col3:
        if avg_l > 0 and avg_s > 0: st.success("✅ 매수 신호 (상승장)")
        elif avg_l < 0 and avg_s < 0: st.error("🚨 도망챠! (하락장)")
        else: st.warning("⚠️ 관망 (방향 탐색)")
    st.caption("💡 L/S 스코어가 모두 양수면 매수, 모두 음수면 도망챠!, 그 외는 관망. 객관적인 숫자를 믿으십시오.")
else:
    st.error("🚨 데이터 계산 오류!")

st.markdown("---")

# [5] 메인 탭 (테이블, 카드, 상세 설명 100% 복구)
tab1, tab2, tab3 = st.tabs(["📈 섹터 ETF", "💹 개별 종목", "🎯 11개 핵심 섹터"])

with tab1:
    st.subheader("📈 섹터 ETF 스코어 (S-L 순위)")
    sub_t, sub_c = st.tabs(["📑 테이블 뷰", "🎴 카드 뷰"])
    with sub_t: # 소장님 전용 테이블 뷰
        st.dataframe(df_sectors.style.background_gradient(cmap='RdYlGn', subset=['L-score','S-score','S-L','20일(%)']).format({'L-score':'{:.2f}','S-score':'{:.2f}','S-L':'{:.2f}','20일(%)':'{:.2f}%'}), use_container_width=True, height=500)
    with sub_c: # 순정 카드 뷰 (가독성 강화)
        df_card = df_sectors.copy()
        df_card['_o'] = df_card.apply(lambda r: 0 if r['S-score']>0 and r['L-score']>0 else (2 if r['S-score']<0 and r['L-score']<0 else 1), axis=1)
        df_card = df_card.sort_values(['_o','S-L'], ascending=[True, False]).reset_index(drop=True)
        sig_labels, sig_colors = {0:"✅ 매수 신호", 1:"⚠️ 관망", 2:"🚨 도망챠"}, {0:"#d1fae5", 1:"#fef9c3", 2:"#fee2e2"}
        current_sig, cols, col_idx = -1, st.columns(2), 0
        for _, row in df_card.iterrows():
            o = row['_o']
            if o != current_sig:
                current_sig = o
                st.markdown(f"<div style='background:{sig_colors[o]};padding:6px 12px;border-radius:6px;font-weight:700;font-size:0.82rem;margin:10px 0 6px 0;'>{sig_labels[o]}</div>", unsafe_allow_html=True)
                cols, col_idx = st.columns(2), 0
            sc, ic = ["buy-signal","wait-signal","sell-signal"][o], ["✅","⚠️","🚨"][o]
            with cols[col_idx % 2]:
                st.markdown(f'<div class="metric-card {sc}"><div class="ticker-header">{ic} {row["섹터"]} ({row["티커"]})</div><div class="score-box"><b>S-L: {row["S-L"]:.3f}</b> | <b>{row["20일(%)"]:.2f}%</b><br>L: {row["L-score"]:.3f} / S: {row["S-score"]:.3f}</div></div>', unsafe_allow_html=True)
            col_idx += 1
    st.markdown("##### 💡 퀀트 지표 핵심 요약")
    st.caption("**📊 L-score**: 장기 추세 점수 / **🚀 S-score**: 단기 모멘텀 점수")

with tab2:
    st.subheader("💹 개별 종목 추적")
    st.dataframe(df_individual.style.background_gradient(cmap='RdYlGn', subset=['연초대비','200대비']).format({'현재가':'{:.2f}','연초대비':'{:.1f}%','200대비':'{:.1f}%'}), use_container_width=True)

with tab3:
    st.subheader("🎯 11개 핵심 섹터 현황")
    st.dataframe(df_core.style.background_gradient(cmap='RdYlGn', subset=['S-SCORE','20일(%)']).format({'S-SCORE':'{:.2f}','20일(%)':'{:.2f}%'}), use_container_width=True)

# [6] 📉 상세 분석 차트 (완벽 복구 완료)
st.markdown("---")
selected = st.selectbox("📉 상세 분석 차트 선택", list(all_data['sector_etfs'].keys()))
if selected:
    hist = all_data['sector_etfs'][selected]['history'].copy()
    ticker = all_data['sector_etfs'][selected]['ticker']
    if isinstance(hist.columns, pd.MultiIndex): hist.columns = hist.columns.get_level_values(0)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=hist.index, y=hist['Close'].values.flatten(), name='종가', line=dict(color='blue', width=2)))
    if 'MA200' in hist.columns: fig.add_trace(go.Scatter(x=hist.index, y=hist['MA200'].values.flatten(), name='MA200', line=dict(dash='dot', color='green')))
    st.plotly_chart(fig.update_layout(title=f"{selected} ({ticker}) 분석 차트", template="plotly_white", height=450), use_container_width=True)

st.caption("📊 JEFF의 퀀트 매크로 연구소 · 데이터 기반 냉철한 투자")
