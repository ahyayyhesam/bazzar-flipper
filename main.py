import requests
import time
import threading

global api_url
api_url = 'https://api.hypixel.net/skyblock/bazaar'
global api_response  # Keeping your global declaration

def update_api():
    global api_response
    while True:
        api_response = requests.get(api_url).json()
        last_updated = api_response.get('lastUpdated', time.time())
        delay = max(last_updated + 60 - time.time(), 0)
        time.sleep(delay)

# Start the updater thread (keeping your original structure)
threading.Thread(target=update_api).start()