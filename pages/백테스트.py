import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime

st.set_page_config(page_title="CMS 신호 백테스트", page_icon="🚦", layout="wide")

# ── 스타일 설정 ──
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700&display=swap');
html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; }
.block-container { padding-top: 3.5rem !important; }

.stat-card { background: #f8faff; border: 1px solid #dbeafe; border-radius: 10px; padding: 16px; text-align: center; margin-bottom: 10px; }
.stat-num  { font-size: 1.6rem; font-weight: 800; }
.stat-label{ font-size: 0.78rem; color: #6b7280; margin-top: 2px; }

.event-card { border-radius: 8px; padding: 10px 14px; margin-bottom: 8px; font-size: 0.84rem; line-height: 1.5; border-left: 4px solid; }
.ev-safe   { background:#f0fdf4; border-color:#10b981; }
.ev-danger { background:#fef2f2; border-color:#ef4444; }

.sig-green  { color: #059669; font-weight: 800; }
.sig-yellow { color: #d97706; font-weight: 800; }
.sig-red    { color: #dc2626; font-weight: 800; }
.sig-titan  { color: #7c3aed; font-weight: 800; } /* 타이탄 보라색 */
</style>
""", unsafe_allow_html=True)

st.title("🚦 CMS 통합 신호등 백테스트")
st.caption("타이탄 알파 설계도 기반: VIX(공포), OVX(전쟁), Spread(신용)를 융합한 1,000억짜리 방패 엔진입니다.")
st.markdown("---")

# ── 역사적 이벤트 정의 ──
EVENTS = [
    {"date": "2000-03-24", "name": "닷컴버블 붕괴 시작", "type": "danger", "desc": "추세 붕괴 포착. 기계적 현금화 구간"},
    {"date": "2008-09-15", "name": "리먼 파산 (금융위기)", "type": "danger", "desc": "신용 스프레드 폭발 및 🔴빨간불 지속 구간"},
    {"date": "2009-03-09", "name": "금융위기 대바닥", "type": "safe", "desc": "역발상 매수 타점(Purple) 발생 구간"},
    {"date": "2020-02-24", "name": "코로나 팬데믹 폭락", "type": "danger", "desc": "VIX 폭등에 따른 즉각적인 대피 신호"},
    {"date": "2020-03-23", "name": "코로나 최저점", "type": "safe", "desc": "역사적 V자 랠리 출발점 및 역발상 매수 신호"},
    {"date": "2022-01-05", "name": "인플레이션 & 긴축", "type": "danger", "desc": "금리차 역전 및 1년 내내 이어진 베어마켓"},
    {"date": "2025-04-02", "name": "트럼프 관세 충격", "type": "danger", "desc": "단기 노이즈에 대한 추세 방어력 테스트"}
]

# ── 데이터 로딩 ──
@st.cache_data(ttl=3600, show_spinner=False)
def load_macro_data(ticker, start_
