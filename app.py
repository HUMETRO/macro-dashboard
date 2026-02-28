import streamlit as st
import json
import os
from datetime import datetime

st.set_page_config(
    page_title="JEFF 퀀트 매크로 연구소",
    page_icon="🚀",
    layout="centered"  # 모바일 최적화를 위해 중앙 정렬 유지
)

# ✅ 모바일 최적화 및 폰트 설정
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700&display=swap');
html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; }

.hero-box {
    background: linear-gradient(135deg, #0f2027, #203a43, #2c5364);
    color: white;
    padding: 28px 24px;
    border-radius: 16px;
    margin-bottom: 1.2rem;
    text-align: center;
}
.hero-box h2 { font-size: 1.3rem; margin-bottom: 8px; }
.hero-box p  { font-size: 0.88rem; opacity: 0.85; line-height: 1.6; }

/* ⭐ 제자님의 오리지널 모바일 안내 문구 스타일 */
.mobile-tip {
    background: #fff3cd;
    border-left: 4px solid #ffc107;
    padding: 10px 14px;
    border-radius: 8px;
    font-size: 0.82rem;
    margin-bottom: 1.5rem;
    color: #856404;
}

.feature-card {
    background: #f8f9fa;
    border-left: 4px solid #2d6a9f;
    padding: 12px 16px;
    border-radius: 8px;
    margin-bottom: 8px;
    font-size: 0.9rem;
    color: #333;
}

div.stButton > button {
    width: 100%;
    padding: 0.8rem 1rem;
    font-size: 1.1rem;
    font-weight: 700;
    border-radius: 12px;
    background-color: #2d6a9f;
    color: white;
    border: none;
    box-shadow: 0 4px 15px rgba(0,0,0,0.1);
}
</style>
""", unsafe_allow_html=True)

# [1] 히어로 섹션
st.markdown("""
<div class="hero-box">
    <h2>🚀 JEFF의 퀀트 매크로 연구소</h2>
    <p>인간의 감정을 배제하고 <b>객관적인 데이터</b>만으로 시장의 흐름을 읽습니다.<br>
    흔들릴 때, 숫자를 보고 냉철하게 마음을 다잡으십시오.</p>
</div>
""", unsafe_allow_html=True)

# [2] ⭐ 제자님 요청: 모바일 안내 문구 원상복구
st.markdown("""
<div class="mobile-tip">
    📱 <b>모바일 사용자:</b> 왼쪽 상단 <b>[ > ]</b> 버튼을 누르면 전체 메뉴를 볼 수 있어요!
</div>
""", unsafe_allow_html=True)

# [3] ⭐ 제자님 요청: "분석기 실행 눌러라" 지침 복구
st.info("💡 아래 버튼을 눌러 실시간 매크로 위험 분석기를 실행하십시오.")
if st.button("📊 실시간 매크로 위험 분석기 실행 →", use_container_width=True):
    st.switch_page("pages/매크로위험알리미.py")

st.markdown("<br>", unsafe_allow_html=True)

# [4] 주요 기능 안내 (원본 설명 유지)
with st.expander("🔍 연구소 주요 분석 기능", expanded=False):
    st.markdown("""
<div class="feature-card">📊 <b>매크로 위험알리미</b><br>
미국 섹터 ETF와 11개 핵심 섹터의 장단기 추세 분석 → 시장 위험 신호 포착</div>
<div class="feature-card">🎯 <b>S-L 스코어 시스템</b><br>
단기(S) vs 장기(L) 점수 차이로 자금 흐름의 방향과 속도를 수치화</div>
<div class="feature-card">🛡️ <b>미너비니 절대 추세 필터</b><br>
단기 추세 마이너스 섹터는 '떨어지는 칼날'로 자동 강등 처리</div>
<div class="feature-card">🚨 <b>안전자산 쏠림 경보</b><br>
상위 섹터에 방어 자산 집중 시 스마트머니 이탈 신호 실시간 감지</div>
""", unsafe_allow_html=True)

st.markdown("---")

# [5] 방문자 게시판 (클로드 쌤 기능 유지)
st.markdown("### 💬 방문자 의견 게시판")
# ... (게시판 로직은 기존 클로드 교수님 코드와 동일하게 유지하십시오) ...
