import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import sys
sys.path.append('..')

from data_fetcher import get_all_market_data
from calculations import calculate_sector_scores, calculate_core_sector_scores

st.set_page_config(page_title="매크로 위험알리미", page_icon="📊", layout="wide")

st.title("📊 매크로경제 위험알리미")
st.markdown("---")

# 사이드바
with st.sidebar:
    st.info("💡 미국 섹터 ETF의 장단기 스코어를 분석합니다")
    if st.button("🔄 데이터 새로고침"):
        st.cache_data.clear()

# 데이터 로딩
@st.cache_data(ttl=300)
def load_all_data():
    return get_all_market_data()

with st.spinner("⏳ 데이터 로딩 중..."):
    all_data = load_all_data()
    
    df_sectors = calculate_sector_scores(all_data['sector_etfs'])
    df_core = calculate_core_sector_scores(all_data['core_sectors'])

if 'L-score' not in df_sectors.columns or len(df_sectors) == 0:
    st.error("🚨 인터넷 연결 문제 혹은 야후 파이낸스 서버 오류로 데이터를 가져오지 못했습니다. 터미널의 에러 로그를 확인해주세요.")
    st.stop() 

# === 메인 시장 상태 지표 ===
col1, col2, col3 = st.columns(3)
avg_l = df_sectors['L-score'].mean()
avg_s = df_sectors['S-score'].mean()

with col1:
    st.metric("평균 L-score", f"{avg_l:.2f}", delta="장기 추세", delta_color="off")
with col2:
    st.metric("평균 S-score", f"{avg_s:.2f}", delta="단기 모멘텀", delta_color="off")
with col3:
    if avg_l < 0 and avg_s < 0:
        st.error("🚨 버려 버려! (하락장)")
    elif avg_l > 0 and avg_s > 0:
        st.success("✅ 매수 신호 (상승장)")
    else:
        st.warning("⚠️ 관망 (방향 탐색)")

st.caption("💡 **시장 상태 판별 기준:** 30개 전체 섹터의 평균 장기/단기 스코어가 모두 **0보다 크면 '매수'**, 모두 **0보다 작으면 '버려(위험)'**, 그 외는 **'관망'**으로 표시됩니다. 감정에 휘둘리지 말고 객관적인 숫자를 믿으십시오.")

# 안전자산 쏠림 감지 조기경보 시스템
top_5_sectors = df_sectors.head(5)['섹터'].tolist()
safe_assets = ['CASH', '장기국채', '물가연동채', '유틸리티', '필수소비재']
safe_count = sum(1 for sector in top_5_sectors if sector in safe_assets)

if safe_count >= 2:
    st.error(f"🚨 **안전자산 쏠림 경보 발령!** 현재 상위 5개 섹터 중 {safe_count}개가 방어적 자산입니다. 시장의 스마트머니가 위험을 피해 피난하고 있습니다. 주식 비중 확대를 멈추고 관망하십시오!")
elif safe_count == 1:
    st.warning("⚠️ **안전자산 상승 주의:** 상위 5위권 내에 방어적 자산이 포착되었습니다. 시장의 변동성에 대비하십시오.")

st.markdown("---")

# 2개 탭으로 분리 (개별 종목 탭 삭제 완료)
tab1, tab2 = st.tabs(["📈 섹터 ETF", "🎯 11개 핵심 섹터"])

# === 탭1: 섹터 ETF ===
with tab1:
    st.subheader("📈 섹터 ETF 스코어 (S-L 순위)")
    
    def highlight_benchmarks(row):
        sector = row['섹터']
        if sector in ['S&P', 'NASDAQ']:
            return ['background-color: #d9d9d9; font-weight: bold'] * len(row)
        elif sector in ['CASH', '물가연동채', '장기국채']:
            return ['background-color: #e2efda; color: #385723; font-weight: bold'] * len(row)
        elif sector == '타임폴리오':
            return ['background-color: #d9e1f2; font-weight: bold'] * len(row)
        return [''] * len(row)

    subset_cols = ['L-score', 'S-score', 'S-L', '20일(%)']
    
    st.dataframe(
        df_sectors.style
            .apply(highlight_benchmarks, axis=1) 
            .background_gradient(cmap='RdYlGn', subset=subset_cols) 
            .format({
                'R': '{:.0f}',
                'L-score': '{:.2f}',
                'S-score': '{:.2f}',
                'S-L': '{:.2f}',
                '20일(%)': '{:.2f}%' 
            }),
        use_container_width=True,
        height=700
    )
    
    st.markdown("##### 💡 퀀트 지표 핵심 요약")
    st.caption("1️⃣ **S-L (추세 가속도):** 단기 모멘텀(S)에서 장기 모멘텀(L)을 뺀 값입니다. 값이 클수록(초록색) 과거보다 최근 한 달 사이에 돈이 훨씬 더 맹렬하게 몰리고 있음을 뜻합니다.")
    st.caption("2️⃣ **미너비니 절대 추세 필터 (랭킹 보정):** 아무리 S-L 값이 커도, 현재 단기 추세(S-score) 자체가 마이너스(-)인 '떨어지는 칼날' 종목은 가짜 반등(기저효과)으로 간주하여 순위표 최하위권으로 강등시켰습니다.")
    st.caption("3️⃣ **20일(%):** 최근 1개월(약 20거래일) 동안 실제로 내 계좌에 꽂힌 '진짜 수익률 성적표'입니다. S-L 순위와 20일 수익률이 동반 상승하는 섹터가 시장의 진짜 주도주입니다.")
    st.markdown("<br>", unsafe_allow_html=True) 
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("L-score vs S-score")
        df_clean = df_sectors.dropna(subset=['L-score', 'S-score', 'S-L'])
        if not df_clean.empty:
            fig = px.scatter(
                df_clean, x='L-score', y='S-score', text='섹터',
                size=abs(df_clean['S-L']) + 0.1, color='S-L',
                color_continuous_scale='RdYlGn', title="장단기 스코어 분포"
            )
            fig.update_traces(textposition='top center', textfont_size=8)
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
            
    with col2:
        st.subheader("S-L 순위")
        fig = px.bar(
            df_sectors.head(15), x='S-L', y='섹터', orientation='h',
            color='S-L', color_continuous_scale='RdYlGn', title="Top 15 단기-장기 차이"
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)

# === 탭2: 11개 핵심 섹터 ===
with tab2:
    st.subheader("🎯 11개 핵심 섹터 (S&P 500 GICS)")
    st.caption("이 11개 섹터가 미국 경제 전체를 대표합니다")
    
    st.dataframe(
        df_core.style
            .background_gradient(cmap='RdYlGn', subset=['S-SCORE'])
            .format({
                'R1': '{:.0f}',
                'S-SCORE': '{:.2f}'
            }),
        use_container_width=True,
        height=400
    )
    
    fig = px.bar(
        df_core, x='섹터', y='S-SCORE', color='S-SCORE',
        color_continuous_scale='RdYlGn', title="11개 핵심 섹터 단기 모멘텀"
    )
    fig.update_layout(height=400)
    st.plotly_chart(fig, use_container_width=True)

# 개별 차트
st.markdown("---")
st.subheader("📉 개별 섹터 차트")

all_sectors = list(all_data['sector_etfs'].keys())
selected = st.selectbox("섹터 선택", all_sectors)

if selected and selected in all_data['sector_etfs']:
    hist = all_data['sector_etfs'][selected]['history']
    ticker = all_data['sector_etfs'][selected]['ticker']
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=hist.index, y=hist['Close'], name='종가', line=dict(width=2, color='blue')))
    fig.add_trace(go.Scatter(x=hist.index, y=hist['MA20'], name='MA20', line=dict(dash='dash', color='orange')))
    fig.add_trace(go.Scatter(x=hist.index, y=hist['MA200'], name='MA200', line=dict(dash='dot', color='green')))
    
    fig.update_layout(title=f"{selected} ({ticker}) 차트", xaxis_title="날짜", yaxis_title="가격 ($)", height=500)
    st.plotly_chart(fig, use_container_width=True)
