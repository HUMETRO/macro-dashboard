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

# 🎨 CSS (선생님 원본 카드 스타일 유지 + 모바일 반응형 추가)
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700&display=swap');
html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; }

.metric-card {
    background-color: #ffffff;
    border-radius: 8px;
    padding: 10px;
    border: 1px solid #e5e7eb;
    margin-bottom: 5px;
    min-height: 95px;
    min-width: 0;
    word-break: break-word;
}
.buy-signal  { border-left: 5px solid #10b981; background-color: #f0fdf4; }
.sell-signal { border-left: 5px solid #ef4444; background-color: #fef2f2; }
.wait-signal { border-left: 5px solid #f59e0b; background-color: #fffbeb; }

.ticker-header { font-size: 0.85rem; font-weight: 700; color: #111827 !important; margin-bottom: 2px; }
.score-box     { font-size: 0.75rem; color: #374151 !important; line-height: 1.4; }

/* ✅ 모바일 대응 */
@media (max-width: 640px) {
    .block-container { padding: 0.8rem 0.6rem !important; }
    h1 { font-size: 1.2rem !important; }
    .ticker-header { font-size: 0.8rem; }
    .score-box     { font-size: 0.72rem; }
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

    st.caption("💡 시장 상태 판별 기준: 전체 평균 장기/단기 스코어가 모두 0보다 크면 '매수', 모두 0보다 작으면 '도망챠!', 그 외는 '관망'입니다. 객관적인 숫자를 믿으십시오.")
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

# ✅ 모바일 이용자 안내
st.info("📱 모바일에서 표가 잘리면 **테이블을 좌우로 스크롤**하거나 **카드 뷰**를 이용하세요!")

# [6] 메인 탭 구성
tab1, tab2, tab3 = st.tabs(["📈 섹터 ETF", "💹 개별 종목", "🎯 11개 핵심 섹터"])

# ──────────────────────────────────────────────────
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
        # ✅ 데스크탑 4열 유지 (선생님 원본)
        cols = st.columns(4)
        for idx, row in df_sectors.iterrows():
            with cols[idx % 4]:
                sig  = "buy-signal"  if (row['S-score'] > 0 and row['L-score'] > 0) else \
                       "sell-signal" if (row['S-score'] < 0 and row['L-score'] < 0) else "wait-signal"
                icon = "✅" if sig == "buy-signal" else ("🚨" if sig == "sell-signal" else "⚠️")
                st.markdown(f"""
<div class="metric-card {sig}">
    <div class="ticker-header">{icon} {row['섹터']} ({row['티커']})</div>
    <div class="score-box">
        <b>S-L: {row['S-L']:.3f}</b> | <b>{row['20일(%)']:.2f}%</b><br>
        L: {row['L-score']:.3f} / S: {row['S-score']:.3f}
    </div>
</div>
""", unsafe_allow_html=True)

    # 지표 설명 (원본 문구 100% 유지)
    st.markdown("##### 💡 퀀트 지표 핵심 요약")
    st.caption("**📊 L-score (장기 체력)**: 200일선 이격도, 52주 고점 위치 등을 종합한 장기 추세 점수입니다.")
    st.caption("**🚀 S-score (단기 기세)**: 20일선 이격도, 1개월 수익률 등을 종합한 단기 모멘텀 점수입니다.")
    st.caption("---")
    st.caption("1️⃣ **S-L (추세 가속도):** 단기 모멘텀(S)에서 장기 모멘텀(L)을 뺀 값입니다. 값이 클수록 최근 돈이 맹렬하게 몰리고 있음을 뜻합니다.")
    st.caption("2️⃣ **미너비니 절대 추세 필터 (랭킹 보정)**")
    st.caption("- 단기 추세(S-score)가 마이너스(-)인 섹터는 '하락 추세 속의 일시적 반등'일 뿐입니다.")
    st.caption("- 이런 '떨어지는 칼날'은 가짜 신호로 간주하여 순위표 최하위권으로 강제 강등시켰습니다.")
    st.caption("3️⃣ **20일(%):** 최근 1개월간의 실제 수익률 성적표입니다.")

# ──────────────────────────────────────────────────
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

# ──────────────────────────────────────────────────
with tab3:
    st.subheader("🎯 11개 핵심 섹터 현황")
    st.dataframe(
        df_core.style
            .background_gradient(cmap='RdYlGn', subset=['S-SCORE', '20일(%)'])
            .format({'S-SCORE': '{:.2f}', '20일(%)': '{:.2f}%'}),
        use_container_width=True, height=450
    )

# [7] 차트 (MultiIndex 완벽 대응)
st.markdown("---")
selected = st.selectbox("📉 상세 분석 차트 선택", list(all_data['sector_etfs'].keys()))

if selected:
    hist   = all_data['sector_etfs'][selected]['history'].copy()
    ticker = all_data['sector_etfs'][selected]['ticker']

    # ✅ MultiIndex 정규화
    if isinstance(hist.columns, pd.MultiIndex):
        hist.columns = hist.columns.get_level_values(0)

    date_list = hist.index.tolist()

    # ✅ 1D 배열 보장 헬퍼
    def to_1d(col):
        s = hist[col]
        if isinstance(s, pd.DataFrame):
            s = s.iloc[:, 0]
        return s.values.flatten()

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=date_list, y=to_1d('Close'),
        name='종가', line=dict(color='blue', width=2)
    ))
    if 'MA20' in hist.columns:
        fig.add_trace(go.Scatter(
            x=date_list, y=to_1d('MA20'),
            name='MA20', line=dict(dash='dash', color='orange')
        ))
    if 'MA200' in hist.columns:
        fig.add_trace(go.Scatter(
            x=date_list, y=to_1d('MA200'),
            name='MA200', line=dict(dash='dot', color='green', width=2)
        ))

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
