import yfinance as yf
import pandas as pd
from datetime import datetime
import numpy as np

def get_all_market_data():
    """모든 시장 데이터를 수집하며, 개별 실패에도 시스템이 멈추지 않게 방어합니다."""
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
        'VOO': 'VOO', 'QQQ': 'QQQ', 'SMH': 'SMH', 'SOXL': 'SOXL',
        'BULZ': 'BULZ', 'IBIT': 'IBIT', 'AAPL': 'AAPL', 'MSFT': 'MSFT', 
        'NVDA': 'NVDA', 'GOOG': 'GOOG', 'AMZN': 'AMZN', 'META': 'META', 
        'TSLA': 'TSLA', 'AVGO': 'AVGO', '환율': 'KRW=X', 'VIX': '^VIX' 
    }
    
    core_sectors = {
        '정보기술': 'XLK', '에너지': 'XLE', '금융': 'XLF', '헬스케어': 'XLV',
        '필수소비재': 'XLP', '임의소비재': 'XLY', '산업재': 'XLI', '재료': 'XLB',
        '부동산': 'XLRE', '커뮤니케이션': 'XLC', '유틸리티': 'XLU'
    }
    
    return {
        'sector_etfs': _fetch_data(sector_etfs),
        'individual_stocks': _fetch_data(individual_stocks),
        'core_sectors': _fetch_data(core_sectors)
    }

def _fetch_data(tickers_dict):
    """3년치 데이터를 가져오며 52주 고저점을 정확히 추출합니다."""
    data = {}
    current_year = datetime.now().year
    
    for name, ticker in tickers_dict.items():
        try:
            # 3년치를 가져와야 200일선이 차트 왼쪽 끝까지 나옵니다.
            df = yf.download(ticker, period='3y', interval='1d', progress=False)
            
            if df.empty or len(df) < 20: continue
            
            df.index = pd.to_datetime(df.index).tz_localize(None)
            df['MA20'] = df['Close'].rolling(window=20).mean()
            df['MA200'] = df['Close'].rolling(window=200).mean()
            
            curr_price = float(df['Close'].iloc[-1])
            
            data[name] = {
                'ticker': ticker,
                'current': curr_price,
                'prev_day': float(df['Close'].iloc[-2]),
                'high_52w': float(df['Close'].tail(252).max()),
                'low_52w': float(df['Close'].tail(252).min()),
                'ytd_start': float(df[df.index.year == current_year]['Close'].iloc[0]) if not df[df.index.year == current_year].empty else curr_price,
                'ma200': float(df['MA200'].iloc[-1]),
                'history': df
            }
        except Exception:
            continue
            
    return data
