import streamlit as st
import json
import os
from datetime import datetime

st.set_page_config(page_title="퀀트 매크로 연구소", page_icon="🚀", layout="centered")

# ── 스타일 설정 (글자색 시인성 강화 완료) ──
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700&display=swap');
html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; }
.block-container { padding-top: 3.5rem !important; }

.hero-box {
    background: linear-gradient(135deg, #0f2027, #203a43, #2c5364);
    color: white; padding: 28px 24px; border-radius: 16px; margin-bottom: 1.2rem; text-align: center;
}
.hero-box h2 { font-size: 1.3rem; margin-bottom: 8px; color: white !important; }
.hero-box p  { font-size: 0.88rem; opacity: 0.9; line-height: 1.6; color: white !important; }

/* 💡 수정 포인트: 글자색을 진한 회색(#334155)으로 고정 */
.mobile-tip {
    background: #fff3cd; border-left: 4px solid #ffc107;
    padding: 10px 14px; border-radius: 8px; font-size: 0.82rem; margin-bottom: 1rem;
    color: #334155 !important;
}
.feature-card {
    background: #f8f9fa; border-left: 4px solid #2d6a9f;
    padding: 12px 16px; border-radius: 8px; margin-bottom: 8px; font-size: 0.9rem; line-height: 1.6;
    color: #1e293b !important;
}
.comment-card {
    background: #f1f3f6; border-radius: 10px;
    padding: 12px 16px; margin-bottom: 10px; font-size: 0.87rem; line-height: 1.5;
    color: #1e293b !important;
}
.comment-meta { font-size: 0.74rem; color: #64748b; margin-bottom: 4px; }

.update-card {
    background: #f8faff; border: 1px solid #dbeafe; border-left: 4px solid #3b82f6;
    border-radius: 8px; padding: 12px 16px; margin-bottom: 10px; font-size: 0.86rem; line-height: 1.6;
    color: #1e293b !important;
}
.update-title { font-weight: 700; color: #1e3a5f; margin-bottom: 4px; }
.update-desc  { color: #475569; font-size: 0.83rem; }

div.stButton > button { width:100%; padding:0.7rem 1rem; font-size:1rem; font-weight:700; border-radius:10px; }

@media (max-width: 640px) {
    .block-container { padding-top: 4rem !important; }
    h1 { font-size: 1.3rem !important; }
}
</style>
""", unsafe_allow_html=True)

# ── 기존 로직은 그대로 유지 ──────────────────
BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
COMMENT_FILE = os.path.join(BASE_DIR, "comments.json")
UPDATE_FILE  = os.path.join(BASE_DIR, "updates.json")

TAG_CONFIG = {
    "fix":      ("🔴 버그수정", "tag-fix"),
    "feature": ("🟢 신기능",   "tag-feature"),
    "improve": ("🔵 개선",      "tag-improve"),
    "mobile":  ("🟡 모바일",    "tag-mobile"),
}

DEFAULT_UPDATES = [
    {
        "version": "v0.4",
        "date": "2026-02-28",
        "title": "백테스트 페이지 신설 + 닷컴버블 검증 추가",
        "desc": "과거 경제 위기(닷컴버블, 리먼, 코로나 등) 백테스트 시스템 도입. VIX 및 장단기 금리차 필터 적용.",
        "tags": ["feature", "improve"]
    }
]

def load_json(path, default):
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except: pass
    return default

def save_json(path, data):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except: return False

# ── [1] 히어로 (글자색 시인성 강화 적용) ────────────────
st.markdown("""
<div class="hero-box">
    <h2>🚀 JEFF의 퀀트 매크로 연구소</h2>
    <p>인간의 감정을 배제하고 <b>객관적인 데이터</b>만으로 시장의 흐름을 읽습니다.<br>
    흔들릴 때, 숫자를 보고 냉철하게 마음을 다잡으십시오.</p>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="mobile-tip">
    📱 <b>모바일 사용자:</b> 왼쪽 상단 <b>[ &gt; ]</b> 버튼을 누르면 전체 메뉴를 볼 수 있어요!
</div>
""", unsafe_allow_html=True)

# ── [2] 버튼 및 기능 ────────────────────────────
if st.button("📊 실시간 매크로 위험 분석기 실행 →", use_container_width=True):
    st.switch_page("pages/매크로위험알리미.py")

st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

if st.button("🔬 신호 백테스트 (역사 검증) →", use_container_width=True):
    st.switch_page("pages/백테스트.py")

st.markdown("<br>", unsafe_allow_html=True)

# ── [3] 기능 안내 ────────────────────────────────
with st.expander("🔍 주요 분석 기능 보기", expanded=False):
    st.markdown("""
<div class="feature-card">📊 <b>매크로 위험알리미</b><br>미국 섹터 ETF·개별종목·11개 핵심 섹터 장단기 추세 → 위험 신호 포착</div>
<div class="feature-card">🔬 <b>신호 백테스트</b><br>닷컴버블·2008 리먼·코로나·테이퍼링 등 주요 위기에서 신호 검증</div>
<div class="feature-card">🎯 <b>S-L 스코어 시스템</b><br>단기(S) vs 장기(L) 점수 차이로 자금 흐름의 방향과 속도를 수치화</div>
<div class="feature-card">🚨 <b>안전자산 쏠림 경보</b><br>상위 섹터에 방어 자산 집중 시 스마트머니 이탈 신호 실시간 감지</div>
""", unsafe_allow_html=True)

st.markdown("---")

# ── 방문자 게시판 및 업데이트 로그 (생략, 기존과 동일) ──
# (나머지 소스 코드는 소장님이 가지고 계신 것과 동일하게 유지하시면 됩니다.)
st.caption("📊 JEFF의 퀀트 매크로 연구소 · 데이터 기반 냉철한 투자")
