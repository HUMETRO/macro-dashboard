import streamlit as st
import json
import os
from datetime import datetime

st.set_page_config(page_title="퀀트 매크로 연구소", page_icon="🚀", layout="centered")

# ── 스타일 설정 (글자색 시인성 강화 및 모든 카드 복구) ──
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
.update-version { font-size: 0.72rem; font-weight: 700; color: #3b82f6; letter-spacing: 0.05em; margin-bottom: 3px; }
.update-date    { font-size: 0.7rem; color: #9ca3af; margin-bottom: 6px; }
.update-title   { font-weight: 700; color: #1e3a5f; margin-bottom: 4px; }
.update-desc    { color: #475569; font-size: 0.83rem; }

.tag { display:inline-block; padding:1px 7px; border-radius:10px; font-size:0.68rem; font-weight:600; margin-right:4px; margin-bottom:4px; }
.tag-fix     { background:#fee2e2; color:#dc2626; }
.tag-feature { background:#d1fae5; color:#059669; }
.tag-improve { background:#dbeafe; color:#2563eb; }
.tag-mobile  { background:#fef9c3; color:#d97706; }

div.stButton > button { width:100%; padding:0.7rem 1rem; font-size:1rem; font-weight:700; border-radius:10px; }

@media (max-width: 640px) {
    .block-container { padding-top: 4rem !important; }
    h1 { font-size: 1.3rem !important; }
}
</style>
""", unsafe_allow_html=True)

BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
COMMENT_FILE = os.path.join(BASE_DIR, "comments.json")
UPDATE_FILE  = os.path.join(BASE_DIR, "updates.json")

# 💡 태그 한글화 매핑 딕셔너리
TAG_MAP = {
    "🔴 버그수정": "tag-fix",
    "🟢 신기능": "tag-feature",
    "🔵 개선": "tag-improve",
    "🟡 모바일": "tag-mobile"
}

# 💡 소장님의 잃어버린 V1~V4 실록 복원 데이터
DEFAULT_UPDATES = [
    {
        "version": "v0.4",
        "date": "2026-02-28",
        "title": "역사적 위기 백테스트 시스템 도입",
        "desc": "닷컴버블, 리먼 브라더스, 코로나 팬데믹 등 8대 위기에 대한 종목별 방어율 스토리텔링 뷰 추가. VIX 및 장단기 금리차 필터 적용 완료.",
        "tags": ["🟢 신기능", "🔵 개선"]
    },
    {
        "version": "v0.3",
        "date": "2026-02-26",
        "title": "UI 전면 개편 및 관리자 시스템 신설",
        "desc": "모바일 가독성 극대화를 위한 고대비 통합 카드 시스템(Unified Card) 적용. 연구소 방문자 댓글 관리자 삭제/수정 기능 추가.",
        "tags": ["🟡 모바일", "🟢 신기능"]
    },
    {
        "version": "v0.2",
        "date": "2026-02-24",
        "title": "개별 종목 추적 및 자산군 분류 알고리즘 탑재",
        "desc": "M7 코어 우량주(🟩), 위성 자산(🟨), 레버리지 및 고변동성(🟥) 자동 분류 로직 적용. 200일선 및 연초대비 수익률 트래킹 구축.",
        "tags": ["🟢 신기능", "🔵 개선"]
    },
    {
        "version": "v0.1",
        "date": "2026-02-22",
        "title": "JEFF 퀀트 매크로 연구소 V1 출범",
        "desc": "L-score(장기 추세) 및 S-score(단기 기세) 기반의 시장 판단 시스템 구축. 매수 신호 / 관망 / 도망챠 3단계 조기경보 시스템 가동 시작.",
        "tags": ["🟢 신기능"]
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

def render_tag(t):
    old_to_new = {"fix": "🔴 버그수정", "feature": "🟢 신기능", "improve": "🔵 개선", "mobile": "🟡 모바일"}
    korean_tag = old_to_new.get(t, t)
    css = TAG_MAP.get(korean_tag, "tag-improve")
    return f'<span class="tag {css}">{korean_tag}</span>'

# ── [1] 히어로 ──────────────────────────────────
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

# ── [2] 바로가기 버튼 2개 ───────────────────────
if st.button("📊 실시간 매크로 위험 분석기 실행 →", use_container_width=True):
    st.switch_page("pages/매크로위험알리미.py")

st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

if st.button("🔬 신호 백테스트 (역사 검증) →", use_container_width=True):
    st.switch_page("pages/백테스트.py")

st.markdown("<br>", unsafe_allow_html=True)

# ── 세션 상태 초기화 ──
if "admin_ok" not in st.session_state:
    st.session_state.admin_ok = False
if "edit_index" not in st.session_state:
    st.session_state.edit_index = None

# ── [3] 기능 안내 ────────────────────────────────
with st.expander("🔍 주요 분석 기능 보기", expanded=False):
    st.markdown("""
<div class="feature-card">📊 <b>매크로 위험알리미</b><br>미국 섹터 ETF·개별종목·11개 핵심 섹터 장단기 추세 → 위험 신호 포착</div>
<div class="feature-card">🔬 <b>신호 백테스트</b><br>닷컴버블·2008 리먼·코로나·테이퍼링 등 주요 위기에서 신호 검증</div>
<div class="feature-card">🎯 <b>S-L 스코어 시스템</b><br>단기(S) vs 장기(L) 점수 차이로 자금 흐름의 방향과 속도를 수치화</div>
<div class="feature-card">🚨 <b>안전자산 쏠림 경보</b><br>상위 섹터에 방어 자산 집중 시 스마트머니 이탈 신호 실시간 감지</div>
""", unsafe_allow_html=True)

st.markdown("---")

# ── [4] 방문자 댓글 ──────────────────
st.markdown("### 💬 방문자 의견 게시판")
st.caption("시장 의견, 기능 제안, 자유로운 생각을 남겨주세요!")

with st.form("comment_form", clear_on_submit=True):
    col_a, col_b = st.columns([1, 2])
    with col_a: nickname = st.text_input("닉네임", placeholder="익명 투자자", max_chars=15)
    with col_b: mood = st.selectbox("시장 분위기", ["😐 중립", "🐂 강세", "🐻 약세", "🤔 관망", "🚀 폭발"])
    comment_text = st.text_area("의견", placeholder="시장 분석, 기능 제안, 자유로운 의견 환영합니다 📝  (최대 300자)", max_chars=300, height=90)
    
    if st.form_submit_button("💬 댓글 등록", use_container_width=True):
        if not comment_text.strip():
            st.warning("내용을 입력해주세요!")
        else:
            comments = load_json(COMMENT_FILE, [])
            comments.insert(0, {
                "nickname": nickname.strip() or "익명 투자자", "mood": mood, "text": comment_text.strip(),
                "time": datetime.now().strftime("%Y-%m-%d %H:%M")
            })
            if save_json(COMMENT_FILE, comments[:100]):
                st.success("✅ 등록되었습니다!")
                st.rerun()

comments = load_json(COMMENT_FILE, [])
if comments:
    st.markdown(f"**총 {len(comments)}개 의견**")
    for i, c in enumerate(comments):
        col1, col2 = st.columns([9, 1])
        with col1:
            st.markdown(f"""
            <div class="comment-card">
                <div class="comment-meta">🙋 <b>{c['nickname']}</b> · {c.get('mood','')} · {c['time']}</div>
                {c['text']}
            </div>""", unsafe_allow_html=True)
        with col2:
            if st.session_state.admin_ok:
                if st.button("🗑️", key=f"del_comment_{i}", help="댓글 삭제"):
                    comments.pop(i)
                    save_json(COMMENT_FILE, comments)
                    st.rerun()

st.markdown("---")

# ── [5] 업데이트 로그 및 관리자 기능 ────────────────
st.markdown("### 📋 업데이트 로그")
st.caption("JEFF님이 직접 기록하는 개선 이력입니다.")

with st.expander("🔐 관리자 로그인", expanded=False):
    if not st.session_state.admin_ok:
        pw = st.text_input("비밀번호", type="password", key="login_pw")
        if st.button("로그인", key="login_btn"):
            if pw == "airbusan3060!": 
                st.session_state.admin_ok = True
                st.rerun()
            else: st.error("비밀번호가 틀렸습니다.")
    else:
        st.success("✅ 관리자로 로그인 중입니다.")
        if st.button("로그아웃", key="logout_btn"):
            st.session_state.admin_ok = False
            st.session_state.edit_index = None
            st.rerun()

if st.session_state.admin_ok:
    with st.expander("➕ 새 업데이트 기록 추가 및 관리", expanded=False):
        with st.form("update_add_form", clear_on_submit=True):
            c1, c2 = st.columns([1, 1])
            with c1: new_version = st.text_input("버전", placeholder="v0.5")
            with c2: new_date    = st.text_input("날짜", value=datetime.now().strftime("%Y-%m-%d"))
            new_title = st.text_input("제목", placeholder="업데이트 제목")
            new_desc  = st.text_area("설명", placeholder="변경 내용을 입력하세요", height=80)
            
            new_tags  = st.multiselect("태그", list(TAG_MAP.keys()))
            
            if st.form_submit_button("📝 추가", use_container_width=True):
                if not new_title.strip(): st.warning("제목을 입력해주세요!")
                else:
                    updates = load_json(UPDATE_FILE, DEFAULT_UPDATES)
                    updates.append({"version": new_version.strip() or "v?", "date": new_date.strip(),
                                    "title": new_title.strip(), "desc": new_desc.strip(), "tags": new_tags})
                    
                    # 💡 [핵심] 버전(version) 기준 내림차순(최신순) 자동 정렬 로직!
                    updates.sort(key=lambda x: x.get('version', ''), reverse=True)
                    
                    if save_json(UPDATE_FILE, updates):
                        st.success("✅ 추가 및 자동 정렬되었습니다!")
                        st.rerun()
        

updates = load_json(UPDATE_FILE, DEFAULT_UPDATES)

# 불러온 데이터도 항상 버전을 기준으로 내림차순 정렬하여 보여줍니다.
updates.sort(key=lambda x: x.get('version', ''), reverse=True)

for i, u in enumerate(updates):
    if st.session_state.edit_index == i:
        with st.form(key=f"edit_form_{i}"):
            st.markdown("#### ✏️ 업데이트 기록 수정")
            c1, c2 = st.columns([1, 1])
            with c1: e_version = st.text_input("버전", value=u.get('version', ''))
            with c2: e_date    = st.text_input("날짜", value=u.get('date', ''))
            e_title = st.text_input("제목", value=u.get('title', ''))
            e_desc  = st.text_area("설명", value=u.get('desc', ''), height=80)
            
            old_to_new = {"fix": "🔴 버그수정", "feature": "🟢 신기능", "improve": "🔵 개선", "mobile": "🟡 모바일"}
            default_tags = [old_to_new.get(t, t) for t in u.get("tags", []) if old_to_new.get(t, t) in TAG_MAP]
            
            e_tags  = st.multiselect("태그", list(TAG_MAP.keys()), default=default_tags)
            
            col_save, col_cancel = st.columns(2)
            with col_save:
                if st.form_submit_button("💾 변경사항 저장", use_container_width=True):
                    updates[i] = {"version": e_version.strip(), "date": e_date.strip(), 
                                  "title": e_title.strip(), "desc": e_desc.strip(), "tags": e_tags}
                    # 💡 수정 후에도 다시 한번 버전 순 정렬!
                    updates.sort(key=lambda x: x.get('version', ''), reverse=True)
                    save_json(UPDATE_FILE, updates)
                    st.session_state.edit_index = None
                    st.rerun()
            with col_cancel:
                if st.form_submit_button("❌ 취소", use_container_width=True):
                    st.session_state.edit_index = None
                    st.rerun()
    else:
        tags_html = "".join(render_tag(t) for t in u.get("tags", []))
        st.markdown(f"""
        <div class="update-card">
            <div class="update-version">{u['version']}</div>
            <div class="update-date">📅 {u['date']}</div>
            <div class="update-title">🔧 {u['title']}</div>
            <div class="update-desc">{u['desc']}</div>
            <div style="margin-top:6px;">{tags_html}</div>
        </div>""", unsafe_allow_html=True)

        if st.session_state.admin_ok:
            c1, c2, c3 = st.columns([1, 1, 8])
            with c1:
                if st.button("✏️", key=f"edit_btn_{i}", help="수정"):
                    st.session_state.edit_index = i
                    st.rerun()
            with c2:
                if st.button("🗑️", key=f"del_update_{i}", help="삭제"):
                    updates.pop(i)
                    save_json(UPDATE_FILE, updates)
                    st.session_state.edit_index = None
                    st.rerun()

st.markdown("---")
st.caption("📊 JEFF의 퀀트 매크로 연구소 · 데이터 기반 냉철한 투자")

