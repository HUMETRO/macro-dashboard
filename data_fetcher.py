import yfinance as yf
import pandas as pd
from datetime import datetime
import numpy as np

def get_all_market_data():
    """모든 시장 데이터를 수집하며, 차트와 계산에 필요한 모든 필드(52주 고저점 등)를 포함합니다."""
    
    sector_etfs = {
        '금속광산': 'XME', '반도체': 'SOXX', '소비': 'XLB', '에너지': 'XLE',
        '바이오테크': 'XBI', '필수소비재': 'XLP', '타임폴리오': '426030.KS',
        '반도체2': 'SMH', '원유가스개발': 'XOP', '산업재': 'XLI', '주택건설': 'XHB',
        '러셀': 'IWM', '소매판매': 'XRT', '헬스케어': 'XLV', '커뮤니케이션': 'XLC',
        '경기소비재': 'XLY', 'S&P': 'SPY', 'NASDAQ': 'QQQ', '유틸리티': 'XLU',
        'CASH': 'BIL', '물가연동채': 'TIP', '부동산': 'XLRE', '네오클라우드': 'WGMI',
        '테크놀로지': 'XLK', '장기국채': 'TLT', '금융': 'XLF', '중국주식': 'FXI',
        'FANG+/3': 'FNGS', '중국인터넷': 'KWEB', '비트코인': 'IBIT'
    }
    
    individual_stocks = {
        'VOO': 'VOO', 'SSO': 'SSO', 'UPRO': 'UPRO', 'QQQ': 'QQQ', 'TQQQ': 'TQQQ', 
        'QQQI': 'QQQI', 'SMH': 'SMH', 'USD': 'UUP', 'SOXX': 'SOXX', 'SOXL': 'SOXL',
        'MAGS': 'MAGS', 'BULZ': 'BULZ', 'SPMO': 'SPMO', 'VGT': 'VGT', 'IBIT': 'IBIT',
        'AAPL': 'AAPL', 'MSFT': 'MSFT', 'NVDA': 'NVDA', 'GOOG': 'GOOG', 'AMZN': 'AMZN', 
        'META': 'META', 'TSLA': 'TSLA', 'TSMC': 'TSM', 'AVGO': 'AVGO', 'BRK.B': 'BRK-B', 
        '환율': 'KRW=X', 'VIX': '^VIX' 
    }
    
    core_sectors = {
        '커뮤니케이션': 'XLC', '임의소비재': 'XLY', '필수소비재': 'XLP',
        '에너지': 'XLE', '금융': 'XLF', '헬스케어': 'XLV',
        '산업재': 'XLI', '재료': 'XLB', '부동산': 'XLRE',
        '정보기술': 'XLK', '유틸리티': 'XLU'
    }
    
    return {
        'sector_etfs': _fetch_data(sector_etfs),
        'individual_stocks': _fetch_data(individual_stocks),
        'core_sectors': _fetch_data(core_sectors)
    }

def _fetch_data(tickers_dict):
    """3년 데이터를 가져와 이동평균 및 52주 지표를 완벽히 계산합니다."""
    data = {}
    current_year = datetime.now().year
    
    for name, ticker in tickers_dict.items():
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period='3y') # 3년치 확보
            
            if hist.empty: continue
            
            hist.index = pd.to_datetime(hist.index).tz_localize(None)
            
            # 지표 계산
            hist['MA20'] = hist['Close'].rolling(window=20).mean()
            hist['MA200'] = hist['Close'].rolling(window=200).mean()
            
            current_price = float(hist['Close'].iloc[-1])
            
            # [수술 완료] calculations.py가 요구하는 모든 필드를 생성
            data[name] = {
                'ticker': ticker,
                'current': current_price,
                'prev_day': float(hist['Close'].iloc[-2]) if len(hist) > 1 else current_price,
                'high_52w': float(hist['Close'].tail(252).max()), # 최근 1년 고점
                'low_52w': float(hist['Close'].tail(252).min()),  # 최근 1년 저점
                'ytd_start': float(hist[hist.index.year == current_year]['Close'].iloc[0]) if not hist[hist.index.year == current_year].empty else current_price,
                'ma200': float(hist['MA200'].iloc[-1]) if not pd.isna(hist['MA200'].iloc[-1]) else np.nan,
                'history': hist
            }
        except Exception as e:
            print(f"❌ {name} 에러: {e}")
            
    return data
