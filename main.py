import requests
import time
import threading
from threading import Lock
from operator import itemgetter

# ===== CONFIGURATION =====
BAZAAR_URL = 'https://api.hypixel.net/v2/skyblock/bazaar'
INVESTMENT = 10_000_000  # 10 million coin base investment
MIN_MARGIN_PCT = 1.5     # 1.5% minimum profit margin
MIN_PRICE = 100          # Minimum price per item to consider (exclusive)
MIN_LIQUIDITY = 500000      # Minimum available items to consider

# ===== SHARED STATE =====
lock = Lock()
api_data = None

def fetch_bazaar():
    global api_data
    while True:
        try:
            response = requests.get(BAZAAR_URL, timeout=15)
            if response.status_code == 200:
                with lock:
                    api_data = response.json()
                    
                last_updated = api_data.get('lastUpdated', time.time()*1000) / 1000
                delay = max(last_updated + 60 - time.time(), 5)
            else:
                delay = 30
                
            time.sleep(delay)
            
        except Exception as e:
            print(f"Connection error: {str(e)[:50]}")
            time.sleep(30)

def analyze_markets():
    while True:
        if not api_data or 'products' not in api_data:
            time.sleep(1)
            continue
            
        opportunities = []
        products = api_data['products']
        
        for product_id, product in products.items():
            try:
                instant_buy = product['sell_summary'][0]['pricePerUnit'] * 1.0075
                instant_sell = product['buy_summary'][0]['pricePerUnit'] * 0.9925
                
                # Price filter check
                if instant_buy <= MIN_PRICE:
                    continue
                
                margin = instant_sell - instant_buy
                margin_pct = (margin / instant_buy) * 100
                
                if margin_pct < MIN_MARGIN_PCT:
                    continue
                    
                quantity = min(int(INVESTMENT / instant_buy), 
                             product['sell_summary'][0]['amount'],
                             product['buy_summary'][0]['amount'])
                
                if quantity < 1:
                    continue
                    
                buy_speed = product['sell_summary'][0]['amount'] / 3600
                sell_speed = product['buy_summary'][0]['amount'] / 3600
                cycle_time = (quantity / min(buy_speed, sell_speed)) if min(buy_speed, sell_speed) > 0 else float('inf')
                
                if cycle_time > 3600:
                    continue
                    
                hourly_profit = (margin * quantity) * (3600 / cycle_time)
                
                opportunities.append({
                    'item': product_id,
                    'margin%': margin_pct,
                    'profit/hr': hourly_profit,
                    'price': instant_buy,
                    'qty': quantity,
                    'liquidity': min(product['sell_summary'][0]['amount'], product['buy_summary'][0]['amount'])
                })
                
            except (KeyError, IndexError):
                continue

        opportunities.sort(key=lambda x: x['profit/hr'] / x['price'], reverse=True)
        
        print(f"\n{' Top 5 Bazaar Opportunities ':=^40}")
        print(f"Config: >{MIN_PRICE:,} coins/item | >{MIN_MARGIN_PCT}% margin")
        print(f"Updated: {time.strftime('%H:%M:%S')}\n")
        
        for idx, opp in enumerate(opportunities[:5]):
            print(f"{idx+1}. {opp['item']}")
            print(f"   Price: {opp['price']:>8,.2f} | Qty: {opp['qty']:>6,}")
            print(f"   Margin: {opp['margin%']:>5.1f}% | Hourly: {opp['profit/hr']:>12,.0f}")
            print(f"   Liquidity: {opp['liquidity']:>10,}\n")
            
        print("="*40 + "\n")
        time.sleep(60)

if __name__ == "__main__":
    threading.Thread(target=fetch_bazaar, daemon=True).start()
    time.sleep(2)
    threading.Thread(target=analyze_markets, daemon=True).start()
    
    try:
        while True: time.sleep(1)
    except KeyboardInterrupt:
        print("Stopped market tracker")