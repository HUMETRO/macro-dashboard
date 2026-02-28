import streamlit as st
import json
import os
from datetime import datetime

# [1] 기본 설정
st.set_page_config(
    page_title="JEFF 퀀트 매크로 연구소",
    page_icon="🚀",
    layout="centered"
)

# 🔒 관리자 비밀번호 (원하는 숫자로 수정하세요!)
ADMIN_PASSWORD = "1234"

# [2] 스타일 시트 (모바일 최적화 및 디자인)
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

.comment-card {
    background: #f1f3f6;
    border-radius: 10px;
    padding: 12px 16px;
    margin-bottom: 5px;
    font-size: 0.87rem;
    color: #333;
}
.comment-meta { font-size: 0.74rem; color: #888; margin-bottom: 4px; }

div.stButton > button {
    width: 100%;
    padding: 0.8rem 1rem;
    font-size: 1.1rem;
    font-weight: 700;
    border-radius: 12px;
    background-color: #2d6a9f;
    color: white;
    box-shadow: 0 4px 15px rgba(0,0,0,0.1);
}
</style>
""", unsafe_allow_html=True)

# [3] 히어로 섹션
st.markdown("""
<div class="hero-box">
    <h2>🚀 JEFF의 퀀트 매크로 연구소</h2>
    <p>인간의 감정을 배제하고 <b>객관적인 데이터</b>만으로 시장의 흐름을 읽습니다.<br>
    흔들릴 때, 숫자를 보고 냉철하게 마음을 다잡으십시오.</p>
</div>
""", unsafe_allow_html=True)

# [4] 제자님 오리지널 안내 가이드 (원본 문구 100% 보존)
st.markdown("""
<div class="mobile-tip">
    📱 <b>안내:</b> 왼쪽 상단 <b>[ > ]</b> 버튼으로 메뉴를 찾기 어려우시다면, <br>
    망설이지 말고 바로 아래 <b>[분석기 실행]</b> 버튼을 눌러주세요!
</div>
""", unsafe_allow_html=True)

# [5] 분석기 실행 버튼
st.info("💡 실시간 매크로 위험 분석기를 시작하시려면 아래 버튼을 클릭하십시오.")
if st.button("📊 실시간 매크로 위험 분석기 실행 →", use_container_width=True):
    st.switch_page("pages/매크로위험알리미.py")

st.markdown("<br>", unsafe_allow_html=True)

# [6] 주요 분석 기능 (4대 핵심 기능 원본 문구 보존)
with st.expander("🔍 연구소 주요 분석 기능 보기", expanded=False):
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

# [7] 💬 방문자 의견 게시판
st.markdown("### 💬 방문자 의견 게시판")

COMMENT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "comments.json")

def load_comments():
    try:
        if os.path.exists(COMMENT_FILE):
            with open(COMMENT_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except: pass
    return []

def save_comments(comments):
    try:
        with open(COMMENT_FILE, "w", encoding="utf-8") as f:
            json.dump(comments, f, ensure_ascii=False, indent=2)
        return True
    except: return False

# ✅ 댓글 작성 폼 (구문 오류 수정 완료)
with st.form("comment_form", clear_on_submit=True):
    c_col1, c_col2 = st.columns([1, 2])
    with c_col1:
        nick = st.text_input("닉네임", placeholder="익명 투자자", max_chars=15)
    with c_col2:
        mood = st.selectbox("시장 분위기", ["😐 중립", "🐂 강세", "🐻 약세", "🤔 관망", "🚀 폭발"])
    text = st.text_area("의견", placeholder="시장에 대한 생각을 남겨주세요 📝", max_chars=300, height=90)
    
    if st.form_submit_button("💬 댓글 등록", use_container_width=True):
        if text.strip():
            cms = load_comments()
            cms.insert(0, {
                "nickname": nick.strip() or "익명 투자자", 
                "mood": mood, 
                "text": text.strip(), 
                "time": datetime.now().strftime("%Y-%m-%d %H:%M")
            })
            if save_comments(cms[:100]):
                st.success("✅ 등록되었습니다!")
                st.rerun()

# [8] 댓글 목록 및 소장님 전용 삭제 관리
cms = load_comments()
for idx, c in enumerate(cms):
    col_text, col_del = st.columns([9, 1])
    
    with col_text:
        st.markdown(f"""
        <div class="comment-card">
            <div class="comment-meta">🙋 <b>{c['nickname']}</b> · {c.get('mood', '')} · {c['time']}</div>
            {c['text']}
        </div>
        """, unsafe_allow_html=True)
    
    with col_del:
        if st.button("🗑️", key=f"btn_del_{idx}"):
            st.session_state[f"confirm_delete_{idx}"] = True

    if st.session_state.get(f"confirm_delete_{idx}"):
        with st.container():
            st.warning(f"'{c['nickname']}'님의 글을 삭제하시겠습니까?")
            pwd = st.text_input("관리자 비번", type="password", key=f"pwd_{idx}")
            c1, c2 = st.columns(2)
            if c1.button("확인", key=f"ok_{idx}"):
                if pwd == ADMIN_PASSWORD:
                    new_cms = [v for i, v in enumerate(cms) if i != idx]
                    if save_comments(new_cms):
                        st.success("삭제 성공!")
                        del st.session_state[f"confirm_delete_{idx}"]
                        st.rerun()
                else: st.error("비번 틀림!")
            if c2.button("취소", key=f"cancel_{idx}"):
                del st.session_state[f"confirm_delete_{idx}"]
                st.rerun()

st.markdown("---")
st.caption("📊 JEFF의 퀀트 매크로 연구소 · 데이터 기반 냉철한 투자")
