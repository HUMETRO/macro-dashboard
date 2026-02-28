import streamlit as st
import json
import os
from datetime import datetime

st.set_page_config(
    page_title="퀀트 매크로 연구소",
    page_icon="🚀",
    layout="centered"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700&display=swap');
html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; }

.block-container { padding-top: 3.5rem !important; }

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
    margin-bottom: 1rem;
}
.feature-card {
    background: #f8f9fa;
    border-left: 4px solid #2d6a9f;
    padding: 12px 16px;
    border-radius: 8px;
    margin-bottom: 8px;
    font-size: 0.9rem;
    line-height: 1.6;
}
.comment-card {
    background: #f1f3f6;
    border-radius: 10px;
    padding: 12px 16px;
    margin-bottom: 10px;
    font-size: 0.87rem;
    line-height: 1.5;
}
.comment-meta { font-size: 0.74rem; color: #888; margin-bottom: 4px; }

.update-card {
    background: #f8faff;
    border: 1px solid #dbeafe;
    border-left: 4px solid #3b82f6;
    border-radius: 8px;
    padding: 12px 16px;
    margin-bottom: 10px;
    font-size: 0.86rem;
    line-height: 1.6;
}
.update-version { font-size: 0.72rem; font-weight: 700; color: #3b82f6; letter-spacing: 0.05em; margin-bottom: 3px; }
.update-date    { font-size: 0.7rem; color: #9ca3af; margin-bottom: 6px; }
.update-title   { font-weight: 700; color: #1e3a5f; margin-bottom: 4px; }
.update-desc    { color: #4b5563; font-size: 0.83rem; }

.tag { display: inline-block; padding: 1px 7px; border-radius: 10px; font-size: 0.68rem; font-weight: 600; margin-right: 4px; margin-bottom: 4px; }
.tag-fix     { background: #fee2e2; color: #dc2626; }
.tag-feature { background: #d1fae5; color: #059669; }
.tag-improve { background: #dbeafe; color: #2563eb; }
.tag-mobile  { background: #fef9c3; color: #d97706; }

div.stButton > button {
    width: 100%;
    padding: 0.7rem 1rem;
    font-size: 1rem;
    font-weight: 700;
    border-radius: 10px;
}
@media (max-width: 640px) {
    .block-container { padding-top: 4rem !important; }
    h1 { font-size: 1.3rem !important; }
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────
# 파일 경로
# ─────────────────────────────────────
BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
COMMENT_FILE = os.path.join(BASE_DIR, "comments.json")
UPDATE_FILE  = os.path.join(BASE_DIR, "updates.json")

TAG_CONFIG = {
    "fix":     ("🔴 버그수정", "tag-fix"),
    "feature": ("🟢 신기능",   "tag-feature"),
    "improve": ("🔵 개선",     "tag-improve"),
    "mobile":  ("🟡 모바일",   "tag-mobile"),
}

DEFAULT_UPDATES = [
    {
        "version": "v0.3",
        "date": "2026-02-28",
        "title": "모바일 UI 전면 개선 + 댓글 기능 추가",
        "desc": "모바일 상단 메뉴 가림 현상 수정, 카드뷰 2열 정렬, 색상별 그룹 분류 적용",
        "tags": ["mobile", "fix", "feature"]
    },
    {
        "version": "v0.2",
        "date": "2026-02-01",
        "title": "data_fetcher auto_adjust 적용 + MultiIndex 대응",
        "desc": "로컬/클라우드 데이터 불일치 문제 해결. yfinance 최신 버전 MultiIndex 구조 완벽 대응",
        "tags": ["fix", "improve"]
    },
    {
        "version": "v0.1",
        "date": "2026-01-01",
        "title": "최초 배포",
        "desc": "섹터 ETF S-L 스코어, 개별 종목 추적, 11개 핵심 섹터 분석 기능 론칭",
        "tags": ["feature"]
    }
]

def load_json(path, default):
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return default

def save_json(path, data):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False

# ─────────────────────────────────────
# [1] 히어로 섹션
# ─────────────────────────────────────
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

# ─────────────────────────────────────
# [2] 바로가기 버튼
# ─────────────────────────────────────
if st.button("📊 실시간 매크로 위험 분석기 실행 →", use_container_width=True):
    st.switch_page("pages/매크로위험알리미.py")

st.markdown("<br>", unsafe_allow_html=True)

# ─────────────────────────────────────
# [3] 주요 기능 안내
# ─────────────────────────────────────
with st.expander("🔍 주요 분석 기능 보기", expanded=False):
    st.markdown("""
<div class="feature-card">📊 <b>매크로 위험알리미</b><br>미국 섹터 ETF와 11개 핵심 섹터의 장단기 추세 분석 → 시장 위험 신호 포착</div>
<div class="feature-card">🎯 <b>S-L 스코어 시스템</b><br>단기(S) vs 장기(L) 점수 차이로 자금 흐름의 방향과 속도를 수치화</div>
<div class="feature-card">🛡️ <b>미너비니 절대 추세 필터</b><br>단기 추세 마이너스 섹터는 '떨어지는 칼날'로 자동 강등 처리</div>
<div class="feature-card">🚨 <b>안전자산 쏠림 경보</b><br>상위 섹터에 방어 자산 집중 시 스마트머니 이탈 신호 실시간 감지</div>
""", unsafe_allow_html=True)

st.markdown("---")

# ─────────────────────────────────────
# ✅ [4] 방문자 댓글 게시판 (위로 이동)
# ─────────────────────────────────────
st.markdown("### 💬 방문자 의견 게시판")
st.caption("시장 의견, 기능 제안, 자유로운 생각을 남겨주세요!")

with st.form("comment_form", clear_on_submit=True):
    col_a, col_b = st.columns([1, 2])
    with col_a:
        nickname = st.text_input("닉네임", placeholder="익명 투자자", max_chars=15)
    with col_b:
        mood = st.selectbox("시장 분위기", ["😐 중립", "🐂 강세", "🐻 약세", "🤔 관망", "🚀 폭발"])
    comment_text = st.text_area("의견", placeholder="시장 분석, 기능 제안, 자유로운 의견 환영합니다 📝  (최대 300자)", max_chars=300, height=90)
    if st.form_submit_button("💬 댓글 등록", use_container_width=True):
        if not comment_text.strip():
            st.warning("내용을 입력해주세요!")
        else:
            comments = load_json(COMMENT_FILE, [])
            comments.insert(0, {
                "nickname": nickname.strip() or "익명 투자자",
                "mood":     mood,
                "text":     comment_text.strip(),
                "time":     datetime.now().strftime("%Y-%m-%d %H:%M")
            })
            if save_json(COMMENT_FILE, comments[:100]):
                st.success("✅ 등록되었습니다!")
                st.rerun()
            else:
                st.error("저장 실패.")

comments = load_json(COMMENT_FILE, [])
if comments:
    st.markdown(f"**총 {len(comments)}개 의견**")
    for c in comments:
        st.markdown(f"""
<div class="comment-card">
    <div class="comment-meta">🙋 <b>{c['nickname']}</b> · {c.get('mood','')} · {c['time']}</div>
    {c['text']}
</div>
""", unsafe_allow_html=True)
else:
    st.info("아직 등록된 의견이 없습니다. 첫 번째 의견을 남겨보세요! 🎉")

st.markdown("---")

# ─────────────────────────────────────
# ✅ [5] 업데이트 로그 (아래로 이동 + 수정/삭제 기능 추가)
# ─────────────────────────────────────
st.markdown("### 📋 업데이트 로그")
st.caption("JEFF님이 직접 기록하는 개선 이력입니다.")

# 관리자 인증 (session_state로 로그인 유지)
if "admin_ok" not in st.session_state:
    st.session_state.admin_ok = False

with st.expander("🔐 관리자 로그인", expanded=False):
    if not st.session_state.admin_ok:
        pw = st.text_input("비밀번호", type="password", key="login_pw")
        if st.button("로그인", key="login_btn"):
            if pw == "airbusan3060!":   # ← 원하시는 비밀번호로 변경하세요!
                st.session_state.admin_ok = True
                st.rerun()
            else:
                st.error("비밀번호가 틀렸습니다.")
    else:
        st.success("✅ 관리자로 로그인 중입니다.")
        if st.button("로그아웃", key="logout_btn"):
            st.session_state.admin_ok = False
            st.rerun()

# 새 업데이트 추가 (관리자만)
if st.session_state.admin_ok:
    with st.expander("➕ 새 업데이트 기록 추가", expanded=False):
        with st.form("update_add_form", clear_on_submit=True):
            c1, c2 = st.columns([1, 1])
            with c1:
                new_version = st.text_input("버전", placeholder="v0.4")
            with c2:
                new_date = st.text_input("날짜", value=datetime.now().strftime("%Y-%m-%d"))
            new_title = st.text_input("제목", placeholder="업데이트 제목")
            new_desc  = st.text_area("설명", placeholder="변경 내용을 입력하세요", height=80)
            new_tags  = st.multiselect("태그", ["fix", "feature", "improve", "mobile"])
            if st.form_submit_button("📝 추가", use_container_width=True):
                if not new_title.strip():
                    st.warning("제목을 입력해주세요!")
                else:
                    updates = load_json(UPDATE_FILE, DEFAULT_UPDATES)
                    updates.insert(0, {
                        "version": new_version.strip() or "v?",
                        "date":    new_date.strip(),
                        "title":   new_title.strip(),
                        "desc":    new_desc.strip(),
                        "tags":    new_tags
                    })
                    if save_json(UPDATE_FILE, updates):
                        st.success("✅ 추가되었습니다!")
                        st.rerun()

# 업데이트 목록 표시
updates = load_json(UPDATE_FILE, DEFAULT_UPDATES)

for i, u in enumerate(updates):
    tags_html = "".join(
        f'<span class="tag {TAG_CONFIG.get(t,("",TAG_CONFIG["improve"][1]))[1]}">'
        f'{TAG_CONFIG.get(t,(t,""))[0]}</span>'
        for t in u.get("tags", [])
    )
    st.markdown(f"""
<div class="update-card">
    <div class="update-version">{u['version']}</div>
    <div class="update-date">📅 {u['date']}</div>
    <div class="update-title">🔧 {u['title']}</div>
    <div class="update-desc">{u['desc']}</div>
    <div style="margin-top:6px;">{tags_html}</div>
</div>
""", unsafe_allow_html=True)

    # ✅ 관리자만 수정/삭제 버튼 표시
    if st.session_state.admin_ok:
        btn_col1, btn_col2 = st.columns([1, 1])
        with btn_col1:
            if st.button(f"✏️ 수정", key=f"edit_{i}"):
                st.session_state[f"editing_{i}"] = True
        with btn_col2:
            if st.button(f"🗑️ 삭제", key=f"del_{i}"):
                updates.pop(i)
                save_json(UPDATE_FILE, updates)
                st.success("삭제되었습니다.")
                st.rerun()

        # 수정 폼 (해당 항목 클릭 시 인라인 표시)
        if st.session_state.get(f"editing_{i}", False):
            with st.form(f"edit_form_{i}"):
                st.markdown(f"**'{u['title']}' 수정**")
                c1, c2 = st.columns([1, 1])
                with c1:
                    e_version = st.text_input("버전", value=u['version'], key=f"ev_{i}")
                with c2:
                    e_date = st.text_input("날짜", value=u['date'], key=f"ed_{i}")
                e_title = st.text_input("제목", value=u['title'], key=f"et_{i}")
                e_desc  = st.text_area("설명", value=u['desc'],  key=f"esc_{i}", height=80)
                e_tags  = st.multiselect("태그", ["fix", "feature", "improve", "mobile"],
                                          default=u.get("tags", []), key=f"etg_{i}")
                c_save, c_cancel = st.columns([1, 1])
                with c_save:
                    save_btn = st.form_submit_button("💾 저장", use_container_width=True)
                with c_cancel:
                    cancel_btn = st.form_submit_button("취소", use_container_width=True)

                if save_btn:
                    updates[i] = {
                        "version": e_version.strip(),
                        "date":    e_date.strip(),
                        "title":   e_title.strip(),
                        "desc":    e_desc.strip(),
                        "tags":    e_tags
                    }
                    save_json(UPDATE_FILE, updates)
                    st.session_state[f"editing_{i}"] = False
                    st.success("✅ 수정되었습니다!")
                    st.rerun()
                if cancel_btn:
                    st.session_state[f"editing_{i}"] = False
                    st.rerun()

st.markdown("---")
st.caption("📊 JEFF의 퀀트 매크로 연구소 · 데이터 기반 냉철한 투자")
