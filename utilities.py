import re
import random

BASE_62 = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890'

def generate_short_url():

    short_url = "http://localhost:8000/shortener/"
    code=""
    for i in range(7):
        curr = random.choice(BASE_62)
        short_url += curr
        code += curr


    return (short_url, code)

def is_valid_url(url:str) -> bool:
    # The 'r' before the string denotes a raw string, which handles regex backslashes cleanly
    pattern = r"^(https?:\/\/)?(www\.)?([a-zA-Z0-9-]+\.)+[a-zA-Z]{2,63}(\/[-a-zA-Z0-9()@:%_\+.~#?&//=]*)?$"
    
    # re.match checks if the pattern matches the string from the beginning to the end
    if re.match(pattern, url):
        return True
    return False