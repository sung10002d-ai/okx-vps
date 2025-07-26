# API 키 정보
api_key = "d15fcea5-37de-4621-b0d1-9f3cfee37fcf"
secret = "C18AD2A305B14DD6FFFB332AB8A92655"
password = "Sung6461??"

# 필수 라이브러리
import ccxt
import time
import pandas as pd
from datetime import datetime

# OKX 거래소 연결
exchange = ccxt.okx({
    'apiKey': api_key,
    'secret': secret,
    'password': password,
    'enableRateLimit': True,
    'options': {'defaultType': 'swap'}
})

# ✅ API 설정
api_key = 'YOUR_API_KEY'
secret = 'YOUR_SECRET_KEY'
password = 'YOUR_PASSPHRASE'

exchange = ccxt.okx({
    'apiKey': api_key,
    'secret': secret,
    'password': password,
    'enableRateLimit': True,
    'options': {'defaultType': 'swap'}
})

def assign_leverage(symbol):
    if any(x in symbol for x in ['BTC', 'ETH', 'SOL']):
        return 25
    elif any(x in symbol for x in ['XRP', 'LINK', 'ARB']):
        return 15
    else:
        return 8

def fetch_top_symbols(limit=30):
    tickers = exchange.fetch_tickers()
    usdt_pairs = {k: v for k, v in tickers.items() if k.endswith('/USDT:USDT')}
    sorted_pairs = sorted(usdt_pairs.items(), key=lambda x: x[1]['quoteVolume'], reverse=True)
    return [s for s, _ in sorted_pairs[:limit]]

def compute_rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def calculate_indicators(df):
    df['ema'] = df['close'].ewm(span=20).mean()
    df['rsi'] = compute_rsi(df['close'], 14)
    df['upper'] = df['close'].rolling(20).mean() + 2 * df['close'].rolling(20).std()
    df['lower'] = df['close'].rolling(20).mean() - 2 * df['close'].rolling(20).std()
    return df

def should_enter(df):
    last = df.iloc[-1]
    score = 0
    if last['close'] > last['ema']: score += 1
    if last['rsi'] > 55: score += 1
    if last['close'] > last['upper']: score += 1
    return score >= 2.5

def check_stop_conditions(df, entry, highest):
    last = df.iloc[-1]
    trailing_stop = highest * 0.97
    if last['close'] < entry * 0.975:
        return 'fixed'
    elif last['rsi'] < 35 and last['close'] < last['ema']:
        return 'rsi_breakdown'
    elif last['close'] < last['lower']:
        return 'band_break'
    elif last['close'] <= trailing_stop:
        return 'trailing'
    return None

def log_trade(symbol, entry, exit_price, reason):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open("trade_log.csv", "a") as f:
        f.write(f"{ts},{symbol},{entry},{exit_price},{reason}\\n")

def run_strategy(symbol):
    leverage = assign_leverage(symbol)
    exchange.set_leverage(leverage, symbol)
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe='1m', limit=100)
    df = pd.DataFrame(ohlcv, columns=['time','open','high','low','close','volume'])
    df = calculate_indicators(df)

    if not should_enter(df): return

    entry_price = df['close'].iloc[-1]
    predicted_high = entry_price * 1.021
    tp_price = entry_price + (predicted_high - entry_price) * 0.97
    max_price = entry_price

    print(f"[{symbol}] 진입: {entry_price}, TP_PREDICT: {tp_price:.2f}")
    log_trade(symbol, entry_price, tp_price, 'ENTRY')

    while True:
        time.sleep(10)
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe='1m', limit=50)
        df = pd.DataFrame(ohlcv, columns=['time','open','high','low','close','volume'])
        df = calculate_indicators(df)
        now = df['close'].iloc[-1]
        max_price = max(max_price, now)

        if now >= tp_price:
            print(f"[{symbol}] TP_PREDICT 익절: {now}")
            log_trade(symbol, entry_price, now, 'TP_PREDICT')
            break

        reason = check_stop_conditions(df, entry_price, max_price)
        if reason:
            print(f"[{symbol}] 손절 ({reason}): {now}")
            log_trade(symbol, entry_price, now, f'STOP_{reason.upper()}')
            break

def main():
    symbols = fetch_top_symbols()
    for sym in symbols[:5]:  # 상위 5종목 실행
        try:
            run_strategy(sym)
        except Exception as e:
            print(f"[{sym}] 오류: {e}")

if __name__ == "__main__":
    main()
