import pandas as pd
import numpy as np

def _safe_float(series, iloc_pos=-1, default=0.0):
    """Series에서 안전하게 float 추출"""
    try:
        val = series.iloc[iloc_pos]
        return float(val) if not pd.isna(val) else default
    except Exception:
        return default

def _safe_return(hist_close, lookback, current):
    """수익률 계산 방어 로직"""
    if len(hist_close) >= lookback:
        past = float(hist_close.iloc[-lookback])
        return (current / past - 1) if past > 0 else 0.0
    return 0.0

def calculate_sector_scores(sector_data):
    """메인 화면에서 찾는 그 부품입니다!"""
    if not sector_data: return pd.DataFrame()
    results = []
    for name, data in sector_data.items():
        try:
            hist = data['history']
            current = data['current']
            ma200 = data.get('ma200', np.nan)
            close = hist['Close']
            ma20 = _safe_float(hist['MA20']) if 'MA20' in hist.columns else np.nan

            # L-score
            ma200_dist = (current / ma200 - 1) if (not pd.isna(ma200) and ma200 > 0) else 0.0
            high_52w, low_52w = data.get('high_52w', current), data.get('low_52w', current)
            pos_52w = ((current - low_52w) / (high_52w - low_52w) if high_52w != low_52w else 0.5)
            ret_6m = _safe_return(close, 126, current)
            l_score = ma200_dist * 0.4 + pos_52w * 0.3 + ret_6m * 0.3

            # S-score
            ma20_dist = (current / ma20 - 1) if (not pd.isna(ma20) and ma20 > 0) else 0.0
            ret_1m = _safe_return(close, 21, current)
            vol_series = close.pct_change().iloc[-20:]
            vol = float(vol_series.std()) if len(vol_series) >= 10 else 0.0
            s_score = ma20_dist * 0.5 + ret_1m * 0.4 - (vol if not pd.isna(vol) else 0.0) * 0.1

            # S-L 및 랭킹용
            ret_20d = _safe_return(close, 20, current) * 100
            s_l_value = s_score - l_score
            rank_score = (s_l_value - 10) if s_score < 0 else s_l_value

            results.append({
                '섹터': name, '티커': data['ticker'],
                'L-score': round(l_score, 3), 'S-score': round(s_score, 3),
                'S-L': round(s_l_value, 3), '20일(%)': round(ret_20d, 2),
                '_rank_score': rank_score
            })
        except: continue

    df = pd.DataFrame(results)
    if not df.empty:
        df = df.sort_values('_rank_score', ascending=False).reset_index(drop=True)
        df = df.drop(columns=['_rank_score'])
        df.insert(0, 'R', range(1, len(df) + 1))
    return df

def calculate_individual_metrics(stock_data):
    if not stock_data: return pd.DataFrame()
    results = []
    for name, data in stock_data.items():
        try:
            current, prev, ytd, h52, l52 = data['current'], data['prev_day'], data['ytd_start'], data['high_52w'], data['low_52w']
            ma200 = data.get('ma200', np.nan)
            def pct(base): return (current/base-1)*100 if base and not pd.isna(base) and base>0 else np.nan
            results.append({
                '티커': name, '현재가': round(current, 2), '연초대비': pct(ytd),
                'high대비': pct(h52), '200대비': pct(ma200), '전일대비': pct(prev), '52저대비': pct(l52)
            })
        except: continue
    return pd.DataFrame(results)

def calculate_core_sector_scores(core_data):
    if not core_data: return pd.DataFrame()
    results = []
    for name, data in core_data.items():
        try:
            hist, current = data['history'], data['current']
            ma20 = _safe_float(hist['MA20']) if 'MA20' in hist.columns else np.nan
            s_score = (current/ma20-1)*0.5 + _safe_return(hist['Close'], 21, current)*0.4
            results.append({'섹터': name, '티커': data['ticker'], 'S-SCORE': round(s_score, 2), '20일(%)': round(_safe_return(hist['Close'], 20, current)*100, 2)})
        except: continue
    df = pd.DataFrame(results).sort_values('S-SCORE', ascending=False).reset_index(drop=True)
    df.insert(0, 'R1', range(1, len(df) + 1))
    return df
