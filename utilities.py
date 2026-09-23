from urllib.parse import urlparse #Used to validate the long url that the user provides
import random

BASE_62 = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890'

def generate_short_url():

    ans = "https://shorten.com/"
    for i in range(7):
        ans += random.choice(BASE_62)

    return ans

def is_valid_url(url:str) -> bool:
    try:
        result = urlparse(url)
        # Check if scheme and netloc (domain) are present
        return all([result.scheme in ['http', 'https'], result.netloc])
    except Exception:
        return False

