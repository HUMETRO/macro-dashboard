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

# 🎨 [디자인 교체] 카드 공통 스타일 (흰색 배제, 시인성 극대화)
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700&display=swap');
html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; }
.block-container { padding-top: 3.5rem !important; }

/* ── 소장님 전용 통합 카드 ── */
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
}

/* 🎨 신호별 포인트 컬러 (글자색 진하게 고정) */
.card-buy  { border-left: 10px solid #10b981; background: #ecfdf5; color: #064e3b !important; } 
.card-wait { border-left: 10px solid #f59e0b; background: #fffbeb; color: #78350f !important; } 
.card-exit { border-left: 10px solid #ef4444; background: #fef2f2; color: #7f1d1d !important; } 

.ticker-label { font-size: 1.1rem; font-weight: 800; margin-bottom: 4px; display: block; }
.signal-text  { font-size: 0.95rem; font-weight: 700; margin-bottom: 6px; display: block; }
.score-line   { font-size: 0.8rem; border-top: 1px solid rgba(0,0,0,0.1); padding-top: 6px; margin-top: 4px; color: #334155; line-height: 1.4; }

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

# [4] 메인 시장 상태 지표
if not df_sectors.empty and 'L-score' in df_sectors.columns:
    col1, col2, col3 = st.columns(3)
    avg_l = df_sectors['L-score'].mean()
    avg_s = df_sectors['S-score'].mean()
    with col1: st.metric("평균 L-score", f"{avg_l:.2f}", delta="장기 체력", delta_color="off")
    with col2: st.metric("평균 S-score", f"{avg_s:.2f}", delta="단기 기세", delta_color="off")
    with col3:
        if   avg_l > 0 and avg_s > 0: st.success("✅ 매수 신호 (상승장)")
        elif avg_l < 0 and avg_s < 0: st.error("🚨 도망챠! (하락장)")
        else:                          st.warning("⚠️ 관망 (방향 탐색)")
    st.caption("💡 L/S 스코어가 모두 양수면 매수, 모두 음수면 도망챠!, 그 외는 관망. 객관적인 숫자를 믿으십시오.")
else:
    st.error("🚨 데이터 계산 오류 발생!")

# [5] 조기경보 시스템
top_5_sectors = df_sectors.head(5)['섹터'].tolist()
safe_assets   = ['CASH', '장기국채', '물가연동채', '유틸리티', '필수소비재']
safe_count    = sum(1 for s in top_5_sectors if s in safe_assets)
if safe_count >= 2:
    st.error(f"🚨 **안전자산 쏠림 경보 발령!** 현재 상위 5개 섹터 중 {safe_count}개가 방어적 자산입니다. "
             "스마트머니가 피난 중입니다. 관망하십시오!")
elif safe_count == 1:
    st.warning("⚠️ **안전자산 상승 주의:** 상위 5위권 내에 방어적 자산이 포착되었습니다.")

st.markdown("---")
st.info("📱 모바일에서 표가 잘리면 **테이블을 좌우로 스크롤**하거나 **카드 뷰**를 이용하세요!")

# [6] 메인 탭
tab1, tab2, tab3 = st.tabs(["📈 섹터 ETF", "💹 개별 종목", "🎯 11개 핵심 섹터"])

# ══════════════════════════════════════
# TAB1: 섹터 ETF
# ══════════════════════════════════════
with tab1:
    st.subheader("📈 섹터 ETF 스코어 (S-L 순위)")
    sub_t, sub_c = st.tabs(["📑 테이블 뷰", "🎴 카드 뷰"])

    with sub_t:
        def hb(row):
            s = row['섹터']
            if s in ['S&P', 'NASDAQ']:      return ['background-color:#d9d9d9;font-weight:bold'] * len(row)
            elif s in ['CASH','물가연동채','장기국채']: return ['background-color:#e2efda;color:#385723;font-weight:bold'] * len(row)
            return [''] * len(row)
        st.dataframe(
            df_sectors.style.apply(hb, axis=1)
                .background_gradient(cmap='RdYlGn', subset=['L-score','S-score','S-L','20일(%)'])
                .format({'L-score':'{:.2f}','S-score':'{:.2f}','S-L':'{:.2f}','20일(%)':'{:.2f}%'}),
            use_container_width=True, height=500
        )

    with sub_c:
        def get_sig_order(row):
            if row['S-score'] > 0 and row['L-score'] > 0: return 0
            if row['S-score'] < 0 and row['L-score'] < 0: return 2
            return 1

        df_card = df_sectors.copy()
        df_card['_o'] = df_card.apply(get_sig_order, axis=1)
        df_card = df_card.sort_values(['_o','S-L'], ascending=[True, False]).reset_index(drop=True)

        sig_labels = {0:"✅ 매수 구간", 1:"⚠️ 관망 구간", 2:"🚨 도망챠 구간"}
        sig_colors = {0:"#d1fae5",     1:"#fef9c3", 2:"#fee2e2"}
        current_sig = -1
        cols = st.columns(2)
        col_idx = 0

        for _, row in df_card.iterrows():
            o = row['_o']
            if o != current_sig:
                current_sig = o
                st.markdown(f"<div style='background:{sig_colors[o]};padding:6px 12px;border-radius:6px;"
                            f"font-weight:700;font-size:0.82rem;margin:10px 0 6px 0; color:#1e293b;'>{sig_labels[o]}</div>",
                            unsafe_allow_html=True)
                col_idx = 0
                cols = st.columns(2)
            
            css = ["card-buy", "card-wait", "card-exit"][o]
            sig_txt = ["✅ 매수 신호", "⚠️ 관망", "🚨 도망챠"][o]
            ic = ["🟢", "🟡", "🔴"][o]
            
            with cols[col_idx % 2]:
                st.markdown(f"""
                <div class="unified-card {css}">
                    <span class="ticker-label">{ic} {row['섹터']} <span style='color:#64748b;font-weight:400;font-size:0.9rem;'>({row['티커']})</span></span>
                    <span class="signal-text">{sig_txt}</span>
                    <div class="score-line">S-L: <b>{row['S-L']:.3f}</b> | 20일: <b>{row['20일(%)']:.2f}%</b><br>
                    L: {row['L-score']:.3f} / S: {row['S-score']:.3f}</div>
                </div>""", unsafe_allow_html=True)
            col_idx += 1

    st.markdown("##### 💡 퀀트 지표 핵심 요약")
    st.caption("**📊 L-score**: 200일선 이격도, 52주 고점 위치 등 장기 추세 점수")
    st.caption("**🚀 S-score**: 20일선 이격도, 1개월 수익률 등 단기 모멘텀 점수")
    st.caption("1️⃣ **S-L**: 클수록 최근 자금 유입 가속 중  2️⃣ **미너비니 필터**: S<0이면 최하위 강등  3️⃣ **20일(%)**: 최근 1개월 실제 수익률")

# ══════════════════════════════════════
# TAB2: 개별 종목 (표와 카드 모두 아이콘 100% 복구 완료)
# ══════════════════════════════════════
with tab2:
    st.subheader("💹 개별 종목 추적")
    sub_t2, sub_c2 = st.tabs(["📑 테이블 뷰", "🎴 카드 뷰"])

    # 💡 [핵심 해결 로직] 표와 카드에 공통으로 아이콘을 박아넣습니다.
    df_display = df_individual.copy()
    
    # 💡 [핵심 해결 로직] M7 등 개별종목 맞춤형 자산군 분류
    def add_asset_icon(tick):
        # 🟥 레버리지 및 고변동성
        if tick in ['TQQQ', 'SOXL', 'UPRO', 'QLD', 'SSO', 'TECL', 'FNGU', 'BULZ', 'NVDL', 'CONL']: 
            return f"🟥 {tick}"
        # 🟩 코어 우량주 (M7 및 주요 ETF)
        elif tick in ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA', 'TSLA', 'SPY', 'QQQ', 'DIA']: 
            return f"🟩 {tick}"
        # 🟨 위성 자산 (기타 개별주)
        else: 
            return f"🟨 {tick}"
        
    df_display['티커_아이콘'] = df_display['티커'].apply(add_asset_icon)
    
    # 💡 [음영 에러 방어] 빈칸(NaN)이 있으면 색칠 로직이 깨지므로 0으로 꽉꽉 채웁니다.
    num_cols = ['연초대비','high대비','200대비','전일대비','52저대비']
    for col in num_cols:
        df_display[col] = pd.to_numeric(df_display[col], errors='coerce').fillna(0)

    with sub_t2:
        # 테이블 컬럼 예쁘게 재배치
        cols_order = ['티커_아이콘', '현재가', '연초대비', 'high대비', '200대비', '전일대비', '52저대비']
        df_table = df_display[cols_order].rename(columns={'티커_아이콘': '티커'})
        
        st.dataframe(
            df_table.style
                .background_gradient(cmap='RdYlGn', subset=num_cols, vmin=-10, vmax=10)
                .format({
                    '현재가':'{:.2f}',
                    '연초대비':'{:.1f}%',
                    'high대비':'{:.1f}%',
                    '200대비':'{:.1f}%',
                    '전일대비':'{:.1f}%',
                    '52저대비':'{:.1f}%'
                }),
            use_container_width=True, height=450
        )
        st.caption("💡 🟩 코어 우량주 / 🟨 위성 자산 / 🟥 레버리지·고변동성")

    with sub_c2: 
        df_stk = df_display.sort_values('연초대비', ascending=False).reset_index(drop=True)
        cols2 = st.columns(2)
        for i, row in df_stk.iterrows():
            ytd = row.get('연초대비', 0)
            ma200 = row.get('200대비', 0)
            prev  = row.get('전일대비', 0)
            high  = row.get('high대비', 0)
            ticker_with_icon = row['티커_아이콘'] # 🟥 TQQQ 형태로 이미 완성됨

            css = "card-buy" if ytd > 0 else ("card-exit" if ytd < 0 else "card-wait")
            sig_txt = "✅ 매수 신호" if ytd > 0 else ("🚨 도망챠" if ytd < 0 else "⚠️ 관망")
            ic = "🟢" if ytd > 0 else ("🔴" if ytd < 0 else "🟡")
            
            ytd_str   = f"{ytd:+.1f}%"
            ma200_str = f"{ma200:+.1f}%"
            prev_str  = f"{prev:+.1f}%"
            high_str  = f"{high:+.1f}%"

            with cols2[i % 2]:
                st.markdown(f"""
                <div class="unified-card {css}">
                    <span class="ticker-label">{ic} {ticker_with_icon} <span style='font-size:0.9rem;font-weight:400'>| ${row['현재가']:,.2f}</span></span>
                    <span class="signal-text">{sig_txt} <span style='font-weight:400'>(YTD: {ytd_str})</span></span>
                    <div class="score-line">
                        전일: <b>{prev_str}</b> | 200일: <b>{ma200_str}</b><br>
                        고점대비: <b>{high_str}</b>
                    </div>
                </div>""", unsafe_allow_html=True)

# ══════════════════════════════════════
# TAB3: 11개 핵심 섹터
# ══════════════════════════════════════
with tab3:
    st.subheader("🎯 11개 핵심 섹터 현황")
    sub_t3, sub_c3 = st.tabs(["📑 테이블 뷰", "🎴 카드 뷰"])

    with sub_t3:
        st.dataframe(
            df_core.style
                .background_gradient(cmap='RdYlGn', subset=['S-SCORE','20일(%)'])
                .format({'S-SCORE':'{:.2f}','20일(%)':'{:.2f}%'}),
            use_container_width=True, height=450
        )

    with sub_c3:
        df_core_sorted = df_core.sort_values('S-SCORE', ascending=False).reset_index(drop=True)
        cols3 = st.columns(2)
        for i, row in df_core_sorted.iterrows():
            sc  = float(row['S-SCORE'])
            ret = float(row['20일(%)'])
            rank = int(row['R1']) if 'R1' in row else i+1
            
            css = "card-buy" if sc > 0.05 else ("card-exit" if sc < -0.05 else "card-wait")
            sig_txt = "✅ 매수 신호" if sc > 0.05 else ("🚨 도망챠" if sc < -0.05 else "⚠️ 관망")
            ic = "🟢" if sc > 0.05 else ("🔴" if sc < -0.05 else "🟡")

            with cols3[i % 2]:
                st.markdown(f"""
                <div class="unified-card {css}">
                    <span class="ticker-label">{ic} #{rank} {row['섹터']} <span style='color:#64748b;font-weight:400;font-size:0.9rem;'>({row['티커']})</span></span>
                    <span class="signal-text">{sig_txt}</span>
                    <div class="score-line">S점수: <b>{sc:+.3f}</b> | 20일 수익: <b>{ret:+.2f}%</b></div>
                </div>""", unsafe_allow_html=True)

# [7] 차트
st.markdown("---")
selected = st.selectbox("📉 상세 분석 차트 선택", list(all_data['sector_etfs'].keys()))
if selected:
    hist   = all_data['sector_etfs'][selected]['history'].copy()
    ticker = all_data['sector_etfs'][selected]['ticker']
    if isinstance(hist.columns, pd.MultiIndex):
        hist.columns = hist.columns.get_level_values(0)
    date_list = hist.index.tolist()

    def to_1d(col):
        s = hist[col]
        if isinstance(s, pd.DataFrame): s = s.iloc[:, 0]
        return s.values.flatten()

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=date_list, y=to_1d('Close'), name='종가', line=dict(color='blue', width=2)))
    if 'MA20'  in hist.columns: fig.add_trace(go.Scatter(x=date_list, y=to_1d('MA20'),  name='MA20',  line=dict(dash='dash', color='orange')))
    if 'MA200' in hist.columns: fig.add_trace(go.Scatter(x=date_list, y=to_1d('MA200'), name='MA200', line=dict(dash='dot',  color='green', width=2)))

    view_days = min(len(hist), 500)
    fig.update_layout(
        title=f"{selected} ({ticker}) 분석 차트", template="plotly_white", height=450,
        xaxis_range=[date_list[-view_days], date_list[-1]], hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=10, r=10, t=50, b=10)
    )
    st.plotly_chart(fig, use_container_width=True)

