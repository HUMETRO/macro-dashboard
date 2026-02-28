import yfinance as yf
import pandas as pd
from datetime import datetime
import numpy as np

def get_all_market_data():
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
        '커뮤니케이션': 'XLC', '임의소비재': 'XLY', '필수소비재': 'XLP', '에너지': 'XLE', 
        '금융': 'XLF', '헬스케어': 'XLV', '산업재': 'XLI', '재료': 'XLB', '부동산': 'XLRE',
        '정보기술': 'XLK', '유틸리티': 'XLU'
    }
    return {'sector_etfs': _fetch_data(sector_etfs), 'individual_stocks': _fetch_data(individual_stocks), 'core_sectors': _fetch_data(core_sectors)}

def _fetch_data(tickers_dict):
    data = {}
    current_year = datetime.now().year
    for name, ticker in tickers_dict.items():
        try:
            hist = yf.download(ticker, period='3y', auto_adjust=True, progress=False)
            if hist.empty: continue
            if isinstance(hist.columns, pd.MultiIndex): hist.columns = hist.columns.get_level_values(0)
            hist.index = pd.to_datetime(hist.index).tz_localize(None)
            hist['Close'] = hist['Close'].ffill().bfill()
            hist['MA20'] = hist['Close'].rolling(window=20).mean()
            hist['MA200'] = hist['Close'].rolling(window=200).mean()
            data[name] = {
                'ticker': ticker, 'current': float(hist['Close'].iloc[-1]),
                'prev_day': float(hist['Close'].iloc[-2]) if len(hist)>1 else float(hist['Close'].iloc[-1]),
                'high_52w': float(hist['Close'].tail(252).max()), 'low_52w': float(hist['Close'].tail(252).min()),
                'ytd_start': float(hist[hist.index.year == current_year]['Close'].iloc[0]) if not hist[hist.index.year == current_year].empty else float(hist['Close'].iloc[-1]),
                'ma200': float(hist['MA200'].dropna().iloc[-1]) if not hist['MA200'].dropna().empty else np.nan,
                'history': hist
            }
        except: continue
    return data
