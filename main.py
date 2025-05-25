import requests
import time
import threading
from threading import Lock
from operator import itemgetter

# Shared state
api_url = 'https://api.hypixel.net/v2/skyblock/bazaar'
api_response = None
lock = Lock()
data_ready = threading.Event()

def update_api():
    global api_response
    while True:
        try:
            response = requests.get(api_url, timeout=10)
            response.raise_for_status()
            with lock:
                api_response = response.json()
                if not data_ready.is_set():
                    data_ready.set()
                
            last_updated = api_response['lastUpdated'] / 1000
            delay = max(last_updated + 60 - time.time(), 0)
            time.sleep(delay)
        except Exception as e:
            print(f"API Error: {str(e)[:100]}")
            time.sleep(30)

def analyze_profits():
    while True:
        with lock:
            if not api_response:
                time.sleep(1)
                continue
                
            profitable_items = []
            for product_id, product in api_response['products'].items():
                try:
                    buy = product['buy_summary'][0]
                    sell = product['sell_summary'][0]
                    
                    # Calculate core values
                    buy_price = buy['pricePerUnit']
                    sell_price = sell['pricePerUnit']
                    buy_volume = buy['amount']
                    sell_volume = sell['amount']
                    
                    # Skip negative margins
                    if sell_price <= buy_price:
                        continue
                        
                    # Calculate fill times for 1m worth
                    buy_fill_time = 1_000_000 / (buy_price * buy_volume) if buy_volume > 0 else float('inf')
                    sell_fill_time = 1_000_000 / (sell_price * sell_volume) if sell_volume > 0 else float('inf')
                    
                    # Use the limiting factor (worst case)
                    limiter = max(buy_fill_time, sell_fill_time)
                    if limiter == 0 or limiter == float('inf'):
                        continue
                        
                    # Calculate hourly potential
                    hourly_volume = 3600 / limiter
                    gross_profit = (sell_price - buy_price) * hourly_volume
                    net_profit = gross_profit * 0.75  # Deduct 25%
                    
                    profitable_items.append({
                        'item': product_id,
                        'margin': sell_price - buy_price,
                        'hourly_profit': net_profit,
                        'buy_price': buy_price,
                        'sell_price': sell_price,
                        'fill_time': limiter
                    })
                    
                except (KeyError, IndexError):
                    continue

            # Sort and display top 10
            profitable_items.sort(key=itemgetter('hourly_profit'), reverse=True)
            print("\nTop Profitable Items:")
            for idx, item in enumerate(profitable_items[:10]):
                print(f"{idx+1}. {item['item']}")
                print(f"   Margin: {item['margin']:.2f} | Hourly Profit: {item['hourly_profit']:,.2f}")
                print(f"   Buy: {item['buy_price']:.2f} | Sell: {item['sell_price']:.2f}")
                print(f"   Fill Time: {item['fill_time']:.2f}s\n")
            
        time.sleep(300)  # Re-analyze every 5 minutes

if __name__ == "__main__":
    threading.Thread(target=update_api, daemon=True).start()
    threading.Thread(target=analyze_profits, daemon=True).start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopped by user")