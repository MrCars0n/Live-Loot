#!/usr/bin/env python3
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import json, sys, time

url = sys.argv[1] if len(sys.argv) > 1 else 'https://www.mercari.com/us/item/m15360818077/'

chrome_options = Options()
chrome_options.add_argument('--headless=new')
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')
chrome_options.add_argument('--disable-gpu')
chrome_options.add_argument('--window-size=1920,1080')
chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36')

driver = webdriver.Chrome(options=chrome_options)
driver.get(url)
WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, 'body')))
time.sleep(3)
soup = BeautifulSoup(driver.page_source, 'html.parser')
driver.quit()

print("=== og:image ===")
og = soup.find('meta', property='og:image')
print(og.get('content') if og else None)

print("\n=== All meta tags with image/photo ===")
for tag in soup.find_all('meta'):
    content = tag.get('content', '')
    if any(x in content for x in ['.jpg', '.jpeg', '.png', '.webp']):
        print(f"  {dict(tag.attrs)}")

print("\n=== img tags (first 15) ===")
for img in soup.find_all('img')[:15]:
    print(f"  src={img.get('src','')[:120]}  alt={img.get('alt','')[:40]}")

print("\n=== __NEXT_DATA__ image/photo keys ===")
nd = soup.find('script', {'id': '__NEXT_DATA__'})
if nd:
    data = json.loads(nd.string)
    def find_images(obj, path='', depth=0):
        if depth > 8:
            return
        if isinstance(obj, dict):
            for k, v in obj.items():
                new_path = f"{path}.{k}"
                if isinstance(v, str) and any(ext in v for ext in ['.jpg', '.jpeg', '.png', '.webp']):
                    print(f"  {new_path} = {v[:120]}")
                find_images(v, new_path, depth + 1)
        elif isinstance(obj, list):
            for i, v in enumerate(obj[:3]):
                find_images(v, f"{path}[{i}]", depth + 1)
    find_images(data)
else:
    print("No __NEXT_DATA__ found")

print("\n=== Scripts containing .jpg URLs ===")
for script in soup.find_all('script'):
    text = script.string or ''
    if '.jpg' in text or '.jpeg' in text:
        # Print surrounding context of first image URL found
        idx = max(text.find('.jpg'), text.find('.jpeg'))
        start = max(0, idx - 100)
        print(f"  ...{text[start:idx+50]}...")
        break