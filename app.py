import streamlit as st
import FinanceDataReader as fdr
import pandas as pd
import plotly.express as px

# 1. 제목 달기
st.title("📈 형님의 실시간 주식 상황판")

# 2. 내 포트폴리오 정의 (나중엔 엑셀 파일에서 불러오게 할 수도 있음)
my_portfolio = {
    '삼성전자': {'code': '005930', 'qty': 100},
    'SK하이닉스': {'code': '000660', 'qty': 50},
}

# 3. 데이터 가져오는 함수 (새로고침 할 때마다 실행됨)
data = []
total_value = 0

st.write("⏳ 실시간 시세 조회 중...")

for name, info in my_portfolio.items():
    df = fdr.DataReader(info['code'], '2024')
    current_price = df['Close'].iloc[-1]
    
    # 전일 대비 등락률 계산
    prev_price = df['Close'].iloc[-2]
    change_rate = (current_price - prev_price) / prev_price * 100
    
    val = current_price * info['qty']
    total_value += val
    
    data.append([name, current_price, info['qty'], val, change_rate])

# 4. 화면에 뿌리기
df_show = pd.DataFrame(data, columns=['종목', '현재가', '수량', '평가금액', '등락률'])

# 총 자산 큼지막하게 보여주기
st.metric(label="💰 총 자산", value=f"{total_value:,.0f} 원")

# 표 보여주기 숫자 예쁘게 보여주기 설정
def color_surprise(val):
    color = 'red' if val > 0 else 'blue'
    return f'color: {color}'


st.dataframe(
    df_show.style.format({
        '현재가': '{:,.0f} 원',    # 1,000 원
        '평가금액': '{:,.0f} 원',  # 1,000 원
        '등락률': '{:.2f} %'       # 0.50 % (소수점 2자리)
        }).applymap(color_surprise, subset=['등락률'])
)


# ------------------------------------------------
# 3. 차트 그리기 (표랑 상관없이 새로운 줄에서 시작)
    
fig = px.pie(df_show, values='평가금액', names='종목', title='내 자산 비중', hole=0.4)
st.plotly_chart(fig)  # <--- 스트림릿 전용 차트 그리기 명령어       

# 버튼 하나 만들기
if st.button('🔄 시세 새로고침'):
    st.rerun()


