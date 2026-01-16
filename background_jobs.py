import random
import time
import math

# We simulate a "Market Cycle" so the graph looks realistic
# instead of just random noise.
def fetch_crypto_data():
    """
    In a real app, this would hit the CoinGecko API and Reddit API.
    For now, we simulate a realistic correlation between Hype and Price.
    """
    
    # Simulate a time-based trend (Sine wave)
    t = time.time()
    trend = math.sin(t / 500) * 20  # Slowly goes up and down
    
    # 1. Generate Hype (Random but influenced by trend)
    # 0 = Everyone hates it, 100 = To The Moon
    base_hype = 50 + trend
    hype_noise = random.randint(-10, 10)
    hype_score = max(0, min(100, base_hype + hype_noise))
    
    # 2. Generate Price (Correlated to Hype)
    # If hype is high, price tends to go up
    base_price = 45000 + (trend * 100)
    price_noise = random.randint(-200, 200)
    
    # If hype is extreme (>80), price pumps harder
    if hype_score > 80:
        price_noise += 500
        
    price = base_price + price_noise

    return {
        'coin': 'Bitcoin',
        'price': round(price, 2),
        'hype': int(hype_score)
    }