def calc_returns_v7(df, start_year):
    df = df.copy()
    start_dt = f"{start_year}-01-01"
    df = df[df.index >= start_dt]
    df['daily_ret'] = df['Close'].pct_change().fillna(0)

    # 1. 기본 Exposure 설정 (V6의 공격성 유지)
    def get_base_exposure(sig):
        if sig == '🟢매수(Green)': return 1.0
        if sig == '🟡관망(Yellow)': return 0.7 
        if sig == '🔥역발상매수': return 0.8
        return 0.0

    df['base_exposure'] = df['신호'].apply(get_base_exposure).shift(1).fillna(0)
    
    # 2. 🛡️ MDD 방어용 트레일링 스탑 로직 추가
    final_exposure = []
    cum_ret = 1.0
    max_cum_ret = 1.0
    
    for i in range(len(df)):
        current_base = df['base_exposure'].iloc[i]
        daily_ret = df['daily_ret'].iloc[i]
        
        # 현재까지의 누적 수익률 계산
        cum_ret *= (1 + daily_ret * current_base)
        # 고점 갱신
        if cum_ret > max_cum_ret:
            max_cum_ret = cum_ret
        
        # 💡 [핵심] 고점 대비 낙폭이 -10% 초과 시 비중 강제 축소
        drawdown = (cum_ret / max_cum_ret) - 1
        if drawdown < -0.10:
            actual_exposure = current_base * 0.3 # 비중 70% 삭감
        else:
            actual_exposure = current_base
            
        final_exposure.append(actual_exposure)

    df['invested'] = final_exposure
    df['strat_ret'] = df['daily_ret'] * df['invested']
    df['cum_strat'] = (1 + df['strat_ret']).cumprod()
    df['cum_bah'] = (1 + df['daily_ret']).cumprod()
    return df
