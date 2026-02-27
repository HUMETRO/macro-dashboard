import yfinance as yf
import pandas as pd
from datetime import datetime
import numpy as np

def get_all_market_data():
    """모든 시장 데이터를 3y 기간으로 수집하여 MA200을 완벽히 확보합니다."""
    
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
    
    # [방어 로직] 하나라도 성공하면 결과를 반환할 수 있게 구조화
    return {
        'sector_etfs': _fetch_data(sector_etfs),
        'individual_stocks': _fetch_data(individual_stocks),
        'core_sectors': _fetch_data(core_sectors)
    }

def _fetch_data(tickers_dict):
    """3년치 데이터를 안정적으로 가져오고 MA200 및 52주 지표를 생성합니다."""
    data = {}
    current_year = datetime.now().year
    
    # 티커들을 리스트로 뽑아 한 번에 다운로드 시도 (속도 및 안정성 향상)
    ticker_list = list(tickers_dict.values())
    
    # 3년치를 통째로 가져옵니다.
    all_hist = yf.download(ticker_list, period='3y', interval='1d', group_by='ticker', progress=False)
    
    for name, ticker in tickers_dict.items():
        try:
            # 단일 티커인지 멀티 티커인지에 따라 데이터 추출 방식 대응
            if len(ticker_list) > 1:
                hist = all_hist[ticker].dropna(subset=['Close'])
            else:
                hist = all_hist.dropna(subset=['Close'])
                
            if hist.empty: continue
            
            # 시간대 제거 및 인덱스 표준화
            hist.index = pd.to_datetime(hist.index).tz_localize(None)
            
            # MA 계산
            hist['MA20'] = hist['Close'].rolling(window=20).mean()
            hist['MA200'] = hist['Close'].rolling(window=200).mean()
            
            current_price = float(hist['Close'].iloc[-1])
            
            # calculations.py 요구 필드 완벽 생성
            data[name] = {
                'ticker': ticker,
                'current': current_price,
                'prev_day': float(hist['Close'].iloc[-2]) if len(hist) > 1 else current_price,
                'high_52w': float(hist['Close'].tail(252).max()),
                'low_52w': float(hist['Close'].tail(252).min()),
                'ytd_start': float(hist[hist.index.year == current_year]['Close'].iloc[0]) if not hist[hist.index.year == current_year].empty else current_price,
                'ma200': float(hist['MA200'].iloc[-1]) if not pd.isna(hist['MA200'].iloc[-1]) else np.nan,
                'history': hist
            }
        except Exception:
            continue
            
    return data
