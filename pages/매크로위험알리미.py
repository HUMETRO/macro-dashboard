import streamlit as st
import plotly.graph_objects as go
import sys
import os
import pandas as pd
import numpy as np
import yfinance as yf

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

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700&display=swap');
html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; }
.block-container { padding-top: 3.5rem !important; }

/* ── 카드 스타일 ── */
.metric-card, .stock-card, .core-card {
    background: #fff; border-radius: 8px; padding: 10px 12px; border: 1px solid #e5e7eb; margin-bottom: 8px; min-width: 0; word-break: break-word;
}
.buy-signal, .stock-up, .core-strong { border-left: 5px solid #10b981; background: #f0fdf4; }
.sell-signal, .stock-down, .core-weak { border-left: 5px solid #ef4444; background: #fef2f2; }
.wait-signal, .core-mid { border-left: 5px solid #f59e0b; background: #fffbeb; }
.stock-flat { border-left: 5px solid #9ca3af; background: #f9fafb; }

.ticker-header, .stock-name, .core-name { font-size: 0.85rem; font-weight: 700; color: #111827; margin-bottom: 3px; }
.score-box, .stock-meta, .core-meta { font-size: 0.75rem; color: #374151; line-height: 1.5; }
.stock-price { font-size: 1.05rem; font-weight: 800; margin-bottom: 2px; }
.core-score { font-size: 1.1rem; font-weight: 800; margin-bottom: 2px; }

@media (max-width: 640px) {
    .block-container { padding-top: 4rem !important; }
    h1 { font-size: 1.2rem !important; }
    .ticker-header, .stock-name, .core-name { font-size: 0.78rem; }
    .score-box, .stock-meta, .core-meta { font-size: 0.68rem; }
}
</style>
""", unsafe_allow_html=True)

st.title("📊 매크로경제 위험알리미")
st.markdown("---")

# 💡 VIX 및 금리차 실시간 수집 엔진
@st.cache_data(ttl=300)
def get_macro_indicators():
    try:
        vix_df = yf.download("^VIX", period="5d", progress=False)['Close']
        tnx_df = yf.download("^TNX", period="5d", progress=False)['Close'] # 10년물
        irx_df = yf.download("^IRX", period="5d", progress=False)['Close'] # 3개월물
        
        vix = vix_df.iloc[-1].item() if isinstance(vix_df, pd.DataFrame) else vix_df.iloc[-1]
        tnx = tnx_df.iloc[-1].item() if isinstance(tnx_df, pd.DataFrame) else tnx_df.iloc[-1]
        irx = irx_df.iloc[-1].item() if isinstance(irx_df, pd.DataFrame) else irx_df.iloc[-1]
        
        return round(vix, 2), round(tnx - irx, 2)
    except: return None, None

@st.cache_data(ttl=300)
def load_all_data():
    return get_all_market_data()

with st.spinner("⏳ 데이터를 분석 중입니다..."):
    all_data      = load_all_data()
    df_sectors    = calculate_sector_scores(all_data['sector_etfs'])
    df_individual = calculate_individual_metrics(all_data['individual_stocks'])
    df_core       = calculate_core_sector_scores(all_data['core_sectors'])
    vix_val, spread_val = get_macro_indicators()

if not df_sectors.empty and 'L-score' in df_sectors.columns:
    st.markdown("#### 🧭 시장 풍향계 (수급 & 매크로)")
    col1, col2, col3, col4 = st.columns(4)
    avg_l = df_sectors['L-score'].mean()
    avg_s = df_sectors['S-score'].mean()
    
    with col1: st.metric("평균 L-score", f"{avg_l:.2f}")
    with col2: st.metric("평균 S-score", f"{avg_s:.2f}")
    with col3:
        if vix_val:
            st.metric("VIX (공포지수)", f"{vix_val}", delta="🔴 위험" if vix_val >= 30 else ("🟡 주의" if vix_val >= 20 else "🟢 안정"), delta_color="off")
        else: st.metric("VIX", "N/A")
    with col4:
        if spread_val is not None:
            st.metric("10Y-3M 금리차", f"{spread_val}%", delta="🔴 역전(침체전조)" if spread_val < 0 else "🟢 정상", delta_color="off")
        else: st.metric("금리차", "N/A")

    if vix_val and vix_val >= 30:
        st.error("🚨 **[초비상] VIX 30 돌파!** 스코어와 무관하게 시장의 공포가 극에 달했습니다. 무조건 생존을 우선하십시오!")
    elif spread_val and spread_val < 0:
        st.warning("⚠️ **[거시 경보] 장단기 금리차 역전!** 경기 침체 우려가 있습니다. 방어적 투자를 권장합니다.")
    else:
        if   avg_l > 0 and avg_s > 0: st.success("✅ 매수 신호 (상승장)")
        elif avg_l < 0 and avg_s < 0: st.error("🚨 도망챠! (하락장)")
        else:                          st.warning("⚠️ 관망 (방향 탐색)")
else: st.error("🚨 데이터 계산 오류 발생!")

top_5_sectors = df_sectors.head(5)['섹터'].tolist()
safe_assets   = ['CASH', '장기국채', '물가연동채', '유틸리티', '필수소비재']
safe_count    = sum(1 for s in top_5_sectors if s in safe_assets)
if safe_count >= 2: st.error(f"🚨 **안전자산 쏠림 경보 발령!** 현재 상위 5개 섹터 중 {safe_count}개가 방어적 자산입니다. 스마트머니가 피난 중입니다. 관망하십시오!")
elif safe_count == 1: st.warning("⚠️ **안전자산 상승 주의:** 상위 5위권 내에 방어적 자산이 포착되었습니다.")

st.markdown("---")
st.info("📱 모바일에서 표가 잘리면 **테이블을 좌우로 스크롤**하거나 **카드 뷰**를 이용하세요!")

tab1, tab2, tab3 = st.tabs(["📈 섹터 ETF", "💹 개별 종목", "🎯 11개 핵심 섹터"])

# ══════════════════════════════════════
# TAB1: 섹터 ETF
# ══════════════════════════════════════
with tab1:
    sub_t, sub_c = st.tabs(["📑 테이블 뷰", "🎴 카드 뷰"])
    with sub_t:
        def hb(row):
            s = row['섹터']
            if s in ['S&P', 'NASDAQ']:      return ['background-color:#d9d9d9;font-weight:bold'] * len(row)
            elif s in ['CASH','물가연동채','장기국채']: return ['background-color:#e2efda;color:#385723;font-weight:bold'] * len(row)
            return [''] * len(row)
        st.dataframe(df_sectors.style.apply(hb, axis=1).background_gradient(cmap='RdYlGn', subset=['L-score','S-score','S-L','20일(%)']).format({'L-score':'{:.2f}','S-score':'{:.2f}','S-L':'{:.2f}','20일(%)':'{:.2f}%'}), use_container_width=True, height=500)

    with sub_c:
        df_card = df_sectors.copy()
        df_card['_o'] = df_card.apply(lambda r: 0 if r['S-score']>0 and r['L-score']>0 else (2 if r['S-score']<0 and r['L-score']<0 else 1), axis=1)
        df_card = df_card.sort_values(['_o','S-L'], ascending=[True, False]).reset_index(drop=True)
        sig_labels, sig_colors = {0:"✅ 매수 신호", 1:"⚠️ 관망", 2:"🚨 도망챠"}, {0:"#d1fae5", 1:"#fef9c3", 2:"#fee2e2"}
        
        current_sig = -1
        cols = st.columns(2)
        col_idx = 0
        for _, row in df_card.iterrows():
            o = row['_o']
            if o != current_sig:
                current_sig = o
                st.markdown(f"<div style='background:{sig_colors[o]};padding:6px 12px;border-radius:6px;font-weight:700;font-size:0.82rem;margin:10px 0 6px 0;'>{sig_labels[o]}</div>", unsafe_allow_html=True)
                col_idx = 0
                cols = st.columns(2)
            sc = ["buy-signal","wait-signal","sell-signal"][o]
            ic = ["✅","⚠️","🚨"][o]
            with cols[col_idx % 2]:
                st.markdown(f"""
<div class="metric-card {sc}">
    <div class="ticker-header">{ic} {row['섹터']} <span style='color:#9ca3af;font-weight:400'>({row['티커']})</span></div>
    <div class="score-box"><b>S-L: {row['S-L']:.3f}</b> | <b>{row['20일(%)']:.2f}%</b><br>L: {row['L-score']:.3f} / S: {row['S-score']:.3f}</div>
</div>""", unsafe_allow_html=True)
            col_idx += 1

    # 💡 퀀트 지표 설명 문구 완벽 복구!
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("##### 💡 퀀트 지표 핵심 요약")
    st.caption("**📊 L-score (장기 체력)**: 200일선 이격도, 52주 고점 위치 등을 종합한 장기 추세 점수입니다.")
    st.caption("**🚀 S-score (단기 기세)**: 20일선 이격도, 1개월 수익률 등을 종합한 단기 모멘텀 점수입니다.")
    st.caption("---")
    st.caption("1️⃣ **S-L (추세 가속도):** 단기 모멘텀(S)에서 장기 모멘텀(L)을 뺀 값입니다. 값이 클수록 최근 돈이 맹렬하게 몰리고 있음을 뜻합니다.")
    st.caption("2️⃣ **미너비니 절대 추세 필터:** S-score < 0 이면 '떨어지는 칼날'로 간주, 순위 최하위로 강제 강등합니다.")
    st.caption("3️⃣ **20일(%):** 최근 1개월간의 실제 수익률 성적표입니다.")

# ══════════════════════════════════════
# TAB2: 개별 종목
# ══════════════════════════════════════
with tab2:
    sub_t2, sub_c2 = st.tabs(["📑 테이블 뷰", "🎴 카드 뷰"])
    with sub_t2:
        st.dataframe(df_individual.style.background_gradient(cmap='RdYlGn', subset=['연초대비','high대비','200대비','전일대비','52저대비'], vmin=-10, vmax=10).format({'현재가':'{:.2f}','연초대비':'{:.1f}%','high대비':'{:.1f}%','200대비':'{:.1f}%','전일대비':'{:.1f}%','52저대비':'{:.1f}%'}), use_container_width=True, height=450)
    with sub_c2:
        df_stk = df_individual.copy().sort_values('연초대비', ascending=False).reset_index(drop=True)
        cols2 = st.columns(2)
        for i, row in df_stk.iterrows():
            ytd, ma200, prev, high = row.get('연초대비', 0), row.get('200대비', 0), row.get('전일대비', 0), row.get('high대비', 0)
            if pd.isna(ytd): ytd = 0
            sc = "stock-up" if ytd > 0 else ("stock-down" if ytd < 0 else "stock-flat")
            ic = "📈" if ytd > 0 else ("📉" if ytd < 0 else "➡️")
            with cols2[i % 2]:
                st.markdown(f"""
<div class="stock-card {sc}">
    <div class="stock-name">{ic} {row['티커']}</div>
    <div class="stock-price" style="color:{'#059669' if ytd>0 else '#dc2626'}">${row['현재가']:,.2f}</div>
    <div class="stock-meta">연초대비: <b>{ytd:+.1f}%</b> &nbsp;|&nbsp; 전일: <b>{prev:+.1f}%</b><br>200일선: <b>{ma200:+.1f}%</b> &nbsp;|&nbsp; 고점대비: <b>{high:+.1f}%</b></div>
</div>""", unsafe_allow_html=True)

# ══════════════════════════════════════
# TAB3: 11개 핵심 섹터
# ══════════════════════════════════════
with tab3:
    sub_t3, sub_c3 = st.tabs(["📑 테이블 뷰", "🎴 카드 뷰"])
    with sub_t3:
        st.dataframe(df_core.style.background_gradient(cmap='RdYlGn', subset=['S-SCORE','20일(%)']).format({'S-SCORE':'{:.2f}','20일(%)':'{:.2f}%'}), use_container_width=True, height=450)
    with sub_c3:
        df_core_sorted = df_core.sort_values('S-SCORE', ascending=False).reset_index(drop=True)
        cols3 = st.columns(2)
        for i, row in df_core_sorted.iterrows():
            sc, ret = float(row['S-SCORE']), float(row['20일(%)'])
            css = "core-strong" if sc > 0.05 else ("core-weak" if sc < -0.05 else "core-mid")
            ic = "🔥" if sc > 0.1 else ("❄️" if sc < -0.1 else "😐")
            rank = int(row['R1']) if 'R1' in row else i+1
            with cols3[i % 2]:
                st.markdown(f"""
<div class="core-card {css}">
    <div class="core-name">{ic} #{rank} {row['섹터']} <span style='color:#9ca3af;font-weight:400'>({row['티커']})</span></div>
    <div class="core-score" style="color:{
