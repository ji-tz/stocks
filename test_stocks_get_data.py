import time
import trader.stocks as stocks
import traceback


def test_get_data(symbol):
    print(f"Testing symbol: {symbol}")
    start_time = time.time()
    try:
        df = stocks.get_data(
            symbol=symbol,
            source='akshare',
            start_date='20250101',
            end_date='20250110',
            force_refresh=True,
            cache_dir='data'
        )
        duration = time.time() - start_time
        print(f"Success: {symbol}")
        print(f"Time taken: {duration:.2f} seconds")
        if df is not None:
            print(f"Rows: {len(df)}")
        else:
            print("Received None instead of DataFrame")
    except Exception as e:
        duration = time.time() - start_time
        print(f"Failed: {symbol}")
        print(f"Time taken: {duration:.2f} seconds")
        print(f"Exception: {e}")
        traceback.print_exc()
    print("-" * 20)


if __name__ == "__main__":
    test_get_data('161725')
    test_get_data('600900')
