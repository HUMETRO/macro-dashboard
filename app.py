import streamlit as st

# 페이지 설정
st.set_page_config(page_title="퀀트 매크로 연구소", page_icon="🚀", layout="wide")

# 대문 타이틀
st.title("🚀 냉철한 데이터 기반 투자 대시보드")
st.markdown("---")

# 환영 인사 및 소개
st.header("환영합니다, JEFF님의 투자 연구소입니다!")
st.write("")
st.markdown("""
본 대시보드는 인간의 감정을 배제하고 **객관적인 데이터**만을 기반으로 시장의 흐름을 읽기 위해 제작되었습니다.
인간의 감정으로 오판을 하거나 흔들릴 때, 숫자를 보고 냉철하게 마음을 다잡으십시오.
""")

st.markdown("<br>", unsafe_allow_html=True)

# 💡 [핵심 솔루션] 친구들을 위한 중앙 바로가기 버튼 섹션
col1, col2, col3 = st.columns([1, 2, 1])

with col2:
    st.info("👇 사이드바 메뉴를 찾기 어려우신가요? 아래 버튼을 클릭하세요!")
    # 버튼 클릭 시 분석 페이지로 바로 이동하는 마법의 버튼
    if st.button("📊 실시간 매크로 위험 분석기 실행", use_container_width=True):
        # pages 폴더 내의 파일명을 정확히 입력해야 합니다.
        # 파일명이 '매크로위험알리미.py'라면 아래처럼 작성하세요.
        st.switch_page("pages/매크로위험알리미.py")

st.markdown("<br>", unsafe_allow_html=True)

# 주요 기능 안내 (가독성 좋게 박스로 감싸기)
with st.expander("🔍 주요 분석 기능 자세히 보기", expanded=True):
    st.markdown("""
    1. **매크로 위험알리미**: 미국 섹터 ETF와 11개 핵심 섹터의 장단기 추세를 분석하여 시장의 위험 신호를 포착합니다.
    2. **객관적 지표**: 미너비니 추세 필터와 S-L 스코어를 통해 시장의 주도주가 어디인지 냉철하게 분석합니다.
    """)

st.markdown("---")
st.caption("💡 모바일 사용자는 왼쪽 상단의 화살표(>)를 눌러 다른 메뉴를 확인하실 수도 있습니다.")
