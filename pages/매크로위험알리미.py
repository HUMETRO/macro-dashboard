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

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700&display=swap');
html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; }

/* ✅ 수정1: 모바일 상단 메뉴바에 제목 가림 방지 - 상단 패딩 추가 */
.block-container {
    padding-top: 3.5rem !important;
}

.metric-card {
    background-color: #ffffff;
    border-radius: 8px;
    padding: 10px;
    border: 1px solid #e5e7eb;
    margin-bottom: 8px;
    min-width: 0;
    word-break: break-word;
}
.buy-signal  { border-left: 5px solid #10b981; background-color: #f0fdf4; }
.sell-signal { border-left: 5px solid #ef4444; background-color: #fef2f2; }
.wait-signal { border-left: 5px solid #f59e0b; background-color: #fffbeb; }

.ticker-header { font-size: 0.85rem; font-weight: 700; color: #111827 !important; margin-bottom: 2px; }
.score-box     { font-size: 0.75rem; color: #374151 !important; line-height: 1.5; }

/* ✅ 수정2: 모바일에서 카드 글씨 조정 */
@media (max-width: 640px) {
    .block-container { padding-top: 4rem !important; }
    h1 { font-size: 1.2rem !important; }
    .ticker-header { font-size: 0.78rem; }
    .score-box     { font-size: 0.7rem; }
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
             "시장의 스마트머니가 위험을 피해 피난하고 있습니다. 주식 비중 확대를 멈추고 관망하십시오!")
elif safe_count == 1:
    st.warning("⚠️ **안전자산 상승 주의:** 상위 5위권 내에 방어적 자산이 포착되었습니다. 시장의 변동성에 대비하십시오.")

st.markdown("---")
st.info("📱 모바일에서 표가 잘리면 **테이블을 좌우로 스크롤**하거나 **카드 뷰**를 이용하세요!")

# [6] 메인 탭
tab1, tab2, tab3 = st.tabs(["📈 섹터 ETF", "💹 개별 종목", "🎯 11개 핵심 섹터"])

with tab1:
    st.subheader("📈 섹터 ETF 스코어 (S-L 순위)")
    sub_t, sub_c = st.tabs(["📑 테이블 뷰 (정밀 분석)", "🎴 카드 뷰 (기세 확인)"])

    with sub_t:
        def hb(row):
            s = row['섹터']
            if s in ['S&P', 'NASDAQ']:
                return ['background-color: #d9d9d9; font-weight: bold'] * len(row)
            elif s in ['CASH', '물가연동채', '장기국채']:
                return ['background-color: #e2efda; color: #385723; font-weight: bold'] * len(row)
            return [''] * len(row)

        st.dataframe(
            df_sectors.style
                .apply(hb, axis=1)
                .background_gradient(cmap='RdYlGn', subset=['L-score', 'S-score', 'S-L', '20일(%)'])
                .format({'L-score': '{:.2f}', 'S-score': '{:.2f}', 'S-L': '{:.2f}', '20일(%)': '{:.2f}%'}),
            use_container_width=True, height=500
        )

    with sub_c:
        # ✅ 수정2: 신호별 색깔 순서 정렬 (🟢매수 → 🟡관망 → 🔴매도)
        def get_signal(row):
            if row['S-score'] > 0 and row['L-score'] > 0:
                return 0  # 매수 (상위)
            elif row['S-score'] < 0 and row['L-score'] < 0:
                return 2  # 매도 (하위)
            return 1      # 관망 (중간)

        df_card = df_sectors.copy()
        df_card['_sig_order'] = df_card.apply(get_signal, axis=1)
        # 신호 순서 기준 정렬, 같은 신호 내에서는 S-L 점수 순
        df_card = df_card.sort_values(['_sig_order', 'S-L'], ascending=[True, False]).reset_index(drop=True)

        # 신호 그룹 구분선 표시
        current_sig = -1
        sig_labels  = {0: "✅ 매수 신호", 1: "⚠️ 관망", 2: "🚨 매도 신호"}
        sig_colors  = {0: "#d1fae5", 1: "#fef9c3", 2: "#fee2e2"}

        # ✅ 수정2: 2열 그리드로 모바일 가독성 향상
        cols = st.columns(2)
        col_idx = 0

        for _, row in df_card.iterrows():
            sig_order = row['_sig_order']

            # 신호 그룹이 바뀔 때 구분 헤더 삽입 (전체 너비)
            if sig_order != current_sig:
                current_sig = sig_order
                st.markdown(
                    f"<div style='background:{sig_colors[sig_order]}; padding:6px 12px; "
                    f"border-radius:6px; font-weight:700; font-size:0.82rem; "
                    f"margin: 10px 0 6px 0;'>{sig_labels[sig_order]}</div>",
                    unsafe_allow_html=True
                )
                col_idx = 0  # 새 그룹 시작 시 왼쪽 열부터
                cols = st.columns(2)

            sig_class = ["buy-signal", "wait-signal", "sell-signal"][sig_order]
            icon      = ["✅", "⚠️", "🚨"][sig_order]

            with cols[col_idx % 2]:
                st.markdown(f"""
<div class="metric-card {sig_class}">
    <div class="ticker-header">{icon} {row['섹터']} <span style='color:#9ca3af;font-weight:400;'>({row['티커']})</span></div>
    <div class="score-box">
        <b>S-L: {row['S-L']:.3f}</b> | <b>{row['20일(%)']:.2f}%</b><br>
        L: {row['L-score']:.3f} &nbsp;/&nbsp; S: {row['S-score']:.3f}
    </div>
</div>
""", unsafe_allow_html=True)
            col_idx += 1

    # 지표 설명
    st.markdown("##### 💡 퀀트 지표 핵심 요약")
    st.caption("**📊 L-score (장기 체력)**: 200일선 이격도, 52주 고점 위치 등을 종합한 장기 추세 점수입니다.")
    st.caption("**🚀 S-score (단기 기세)**: 20일선 이격도, 1개월 수익률 등을 종합한 단기 모멘텀 점수입니다.")
    st.caption("---")
    st.caption("1️⃣ **S-L (추세 가속도):** 단기 모멘텀(S)에서 장기 모멘텀(L)을 뺀 값입니다. 값이 클수록 최근 돈이 맹렬하게 몰리고 있음을 뜻합니다.")
    st.caption("2️⃣ **미너비니 절대 추세 필터:** S-score < 0 이면 '떨어지는 칼날'로 간주, 순위 최하위로 강제 강등합니다.")
    st.caption("3️⃣ **20일(%):** 최근 1개월간의 실제 수익률 성적표입니다.")

with tab2:
    st.subheader("💹 개별 종목 추적 (위험도별 분류)")
    st.dataframe(
        df_individual.style
            .background_gradient(
                cmap='RdYlGn',
                subset=['연초대비', 'high대비', '200대비', '전일대비', '52저대비'],
                vmin=-10, vmax=10
            )
            .format({
                '현재가':   '{:.2f}',
                '연초대비': '{:.1f}%',
                'high대비': '{:.1f}%',
                '200대비':  '{:.1f}%',
                '전일대비': '{:.1f}%',
                '52저대비': '{:.1f}%'
            }),
        use_container_width=True, height=450
    )
    st.caption("💡 배경색 의미: 🟩 코어 우량주(안전) / 🟨 위성 자산(주의) / 🟥 레버리지 및 고변동성(위험)")

with tab3:
    st.subheader("🎯 11개 핵심 섹터 현황")
    st.dataframe(
        df_core.style
            .background_gradient(cmap='RdYlGn', subset=['S-SCORE', '20일(%)'])
            .format({'S-SCORE': '{:.2f}', '20일(%)': '{:.2f}%'}),
        use_container_width=True, height=450
    )

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
        if isinstance(s, pd.DataFrame):
            s = s.iloc[:, 0]
        return s.values.flatten()

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=date_list, y=to_1d('Close'), name='종가', line=dict(color='blue', width=2)))
    if 'MA20'  in hist.columns:
        fig.add_trace(go.Scatter(x=date_list, y=to_1d('MA20'),  name='MA20',  line=dict(dash='dash', color='orange')))
    if 'MA200' in hist.columns:
        fig.add_trace(go.Scatter(x=date_list, y=to_1d('MA200'), name='MA200', line=dict(dash='dot',  color='green', width=2)))

    view_days = min(len(hist), 500)
    fig.update_layout(
        title=f"{selected} ({ticker}) 분석 차트",
        template="plotly_white",
        height=450,
        xaxis_range=[date_list[-view_days], date_list[-1]],
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=10, r=10, t=50, b=10)
    )
    st.plotly_chart(fig, use_container_width=True)
