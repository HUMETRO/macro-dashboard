import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime

st.set_page_config(page_title="순수 추세추종 백테스트", page_icon="📈", layout="wide")

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
.ev-watch  { background:#fffbeb; border-color:#f59e0b; }

.signal-buy  { color: #059669; font-weight: 800; }
.signal-sell { color: #dc2626; font-weight: 800; }
.signal-wait { color: #d97706; font-weight: 800; }
</style>
""", unsafe_allow_html=True)

st.title("📈 투자의 규칙(CAN SLIM) 모멘텀 백테스트")
st.caption("매크로 지표의 간섭을 배제하고, 오직 가격 추세(L-S 스코어)에만 집중하여 하락은 피하고 상승은 끝까지 먹는 실전 엔진입니다. (타임머신 버그 수정 완료)")
st.markdown("---")

EVENTS = [
    {"date": "2000-03-24", "name": "닷컴버블 붕괴 시작", "type": "danger", "desc": "추세 붕괴. 기계적 손절을 통한 자산 보호 구역"},
    {"date": "2002-10-09", "name": "닷컴버블 최저점", "type": "safe", "desc": "긴 하락장 종료 후 새로운 강세장(팔로우 스루) 시작"},
    {"date": "2008-09-15", "name": "리먼 파산 (금융위기)", "type": "danger", "desc": "L/S 스코어 전면 붕괴. 완벽한 도망챠 구간"},
    {"date": "2009-03-09", "name": "금융위기 대바닥", "type": "safe", "desc": "강한 반등 모멘텀 발생. 새로운 주도주 랠리 시작"},
    {"date": "2015-08-24", "name": "중국 위안화 쇼크", "type": "danger", "desc": "단기 모멘텀 급락에 따른 기계적 회피"},
    {"date": "2018-10-10", "name": "미중 무역전쟁 폭락", "type": "danger", "desc": "추세 꺾임. 4분기 내내 현금 보유로 방어"},
    {"date": "2020-02-24", "name": "코로나 팬데믹 폭락", "type": "danger", "desc": "역사상 가장 빠른 속도의 추세 붕괴. 즉각 대피"},
    {"date": "2020-04-06", "name": "코로나 V자 반등 확인", "type": "safe", "desc": "S-score(단기 기세) 강한 양수 전환. 칼같은 재탑승"},
    {"date": "2022-01-05", "name": "인플레이션 & 긴축", "type": "danger", "desc": "1년 내내 이어진 하락 추세. 철저한 관망 유지"},
    {"date": "2025-04-02", "name": "트럼프 관세 충격", "type": "danger", "desc": "단기 노이즈에 대한 추세 방어력 테스트"}
]

@st.cache_data(ttl=3600, show_spinner=False)
def load_price_data(ticker, start_year):
    # 추세 계산을 위해 1년 전 데이터부터 미리 당겨옴 (200일선 등 계산용)
    fetch_start = f"{start_year - 1}-01-01"
    df = yf.download(ticker, start=fetch_start, interval='1d', progress=False)
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    df = df[['Close']].rename(columns={'Close': 'Close'})
    df.index = pd.to_datetime(df.index).tz_localize(None)
    return
