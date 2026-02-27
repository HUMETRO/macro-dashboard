import pandas as pd
import numpy as np

def calculate_sector_scores(sector_data):
    """섹터 ETF용: L-score, S-score, S-L, 20일 수익률(%), R 순위"""
    if not sector_data:
        return pd.DataFrame()
        
    results = []
    for name, data in sector_data.items():
        try:
            hist = data['history']
            current = data['current']
            ma200 = data.get('ma200', np.nan)
            ma20 = hist['MA20'].iloc[-1]
            
            # L-score (원래의 정교한 스케일 복구!)
            ma200_dist = (current / ma200 - 1) if not pd.isna(ma200) and ma200 > 0 else 0
            high_52w = data['high_52w']
            low_52w = data['low_52w']
            pos_52w = (current - low_52w) / (high_52w - low_52w) if high_52w != low_52w else 0
            
            if len(hist) >= 126:
                ret_6m = (current / hist['Close'].iloc[-126] - 1)
            else:
                ret_6m = 0
            
            l_score = ma200_dist * 0.4 + pos_52w * 0.3 + ret_6m * 0.3
            
            # S-score (원래 스케일 복구!)
            ma20_dist = (current / ma20 - 1) if not pd.isna(ma20) and ma20 > 0 else 0
            
            if len(hist) >= 21:
                ret_1m = (current / hist['Close'].iloc[-21] - 1)
            else:
                ret_1m = 0
                
            vol = hist['Close'].pct_change().iloc[-20:].std()
            if pd.isna(vol): vol = 0
            
            s_score = ma20_dist * 0.5 + ret_1m * 0.4 - vol * 0.1
            
            # 20일 수익률 (%)
            if len(hist) >= 20:
                ret_20d = (current / hist['Close'].iloc[-20] - 1) * 100
            else:
                ret_20d = 0

            # 💡 [미너비니 절대 추세 필터] 
            s_l_value = s_score - l_score
            # 단기 스코어가 마이너스(하락세)면 순위표에서 -10점을 줘서 무조건 꼴찌 그룹으로 강등!
            rank_score = s_l_value - 10 if s_score < 0 else s_l_value

            results.append({
                '섹터': name,
                '티커': data['ticker'],
                'L-score': round(l_score, 3),
                'S-score': round(s_score, 3),
                'S-L': round(s_l_value, 3),
                '20일(%)': round(ret_20d, 2),
                '_rank_score': rank_score  
            })
        except Exception as e:
            print(f"❌ {name} 계산 실패: {e}")
            
    if not results:
        return pd.DataFrame()
        
    df = pd.DataFrame(results)
    # 랭크 스코어 기준으로 정렬 (비트코인은 여기서 지하로 갑니다)
    df = df.sort_values('_rank_score', ascending=False).reset_index(drop=True)
    df = df.drop(columns=['_rank_score']) 
    df.insert(0, 'R', range(1, len(df) + 1))
    return df

def calculate_individual_metrics(stock_data):
    """개별 종목용"""
    if not stock_data:
        return pd.DataFrame()
        
    results = []
    for name, data in stock_data.items():
        try:
            current = data['current']
            prev = data['prev_day']
            ytd_start = data['ytd_start']
            high_52w = data['high_52w']
            low_52w = data['low_52w']
            ma200 = data.get('ma200', np.nan)
            
            ytd_pct = (current / ytd_start - 1) * 100 if ytd_start > 0 else np.nan
            high_pct = (current / high_52w - 1) * 100 if not pd.isna(high_52w) and high_52w > 0 else np.nan
            ma200_pct = (current / ma200 - 1) * 100 if not pd.isna(ma200) and ma200 > 0 else np.nan
            prev_pct = (current / prev - 1) * 100 if prev > 0 else np.nan
            low_pct = (current / low_52w - 1) * 100 if not pd.isna(low_52w) and low_52w > 0 else np.nan
            
            results.append({
                '티커': name,
                '현재가': round(current, 2),
                '연초대비': ytd_pct,
                'high대비': high_pct,
                '200대비': ma200_pct,
                '전일대비': prev_pct,
                '52저대비': low_pct
            })
        except Exception as e:
            print(f"❌ {name} 계산 실패: {e}")
            
    return pd.DataFrame(results)

def calculate_core_sector_scores(core_data):
    """11개 핵심 섹터용"""
    if not core_data:
        return pd.DataFrame()
        
    results = []
    for name, data in core_data.items():
        try:
            hist = data['history']
            current = data['current']
            ma20 = hist['MA20'].iloc[-1]
            
            ma20_dist = (current / ma20 - 1) if not pd.isna(ma20) and ma20 > 0 else 0
            
            if len(hist) >= 21:
                ret_1m = (current / hist['Close'].iloc[-21] - 1)
            else:
                ret_1m = 0
                
            vol = hist['Close'].pct_change().iloc[-20:].std()
            if pd.isna(vol): vol = 0
            
            # 원래 스케일 복구! (* 100 제거)
            s_score = ma20_dist * 0.5 + ret_1m * 0.4 - vol * 0.1
            
            results.append({
                '섹터': name,
                '티커': data['ticker'],
                'S-SCORE': round(s_score, 2)
            })
        except Exception as e:
            print(f"❌ {name} 계산 실패: {e}")
            
    if not results:
        return pd.DataFrame()
        
    df = pd.DataFrame(results)
    df = df.sort_values('S-SCORE', ascending=False).reset_index(drop=True)
    df.insert(0, 'R1', range(1, len(df) + 1))
    return df
