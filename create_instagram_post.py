#!/usr/bin/env python3

import sys
import io
import time
from PIL import Image, ImageDraw, ImageFont
from urllib.parse import urlparse

try:
    import requests
    from bs4 import BeautifulSoup
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options
    HAS_SELENIUM = True
except ImportError:
    HAS_SELENIUM = False

try:
    import qrcode
    HAS_QRCODE = True
except ImportError:
    HAS_QRCODE = False

def create_qr_code_image(url, size=200):
    try:
        import qrcode
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=2,
        )
        qr.add_data(url)
        qr.make(fit=True)
        
        qr_img = qr.make_image(fill_color="black", back_color="white")
        qr_img = qr_img.resize((size, size), Image.Resampling.LANCZOS)
        return qr_img
    except ImportError:
        pass
    
    try:
        import subprocess
        result = subprocess.run(
            [sys.executable, '-m', 'pip', 'install', 'qrcode[pil]', '--quiet', '--break-system-packages'],
            capture_output=True,
            timeout=30
        )
        if result.returncode == 0:
            import qrcode as qrcode_lib
            qr = qrcode_lib.QRCode(
                version=1,
                error_correction=qrcode_lib.constants.ERROR_CORRECT_H,
                box_size=10,
                border=2,
            )
            qr.add_data(url)
            qr.make(fit=True)
            
            qr_img = qr.make_image(fill_color="black", back_color="white")
            qr_img = qr_img.resize((size, size), Image.Resampling.LANCZOS)
            return qr_img
    except Exception:
        pass
    
    try:
        import segno
        qr = segno.make(url, error='h')
        buffer = io.BytesIO()
        qr.save(buffer, kind='png', scale=5, border=2)
        buffer.seek(0)
        qr_img = Image.open(buffer)
        qr_img = qr_img.resize((size, size), Image.Resampling.LANCZOS)
        return qr_img
    except ImportError:
        pass
    
    img = Image.new('RGB', (size, size), 'white')
    draw = ImageDraw.Draw(img)
    
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14)
    except:
        font = None
    
    text = "Please install:\npip install qrcode[pil]\n\nOr use the URL directly:"
    draw.multiline_text((10, 20), text, fill='black', font=font, align='center')
    
    short_url = url[:30] + "..." if len(url) > 30 else url
    draw.multiline_text((10, size - 60), short_url, fill='black', font=font, align='left')
    
    return img

def fetch_image_with_browser(url):
    if not HAS_SELENIUM:
        print("\n⚠ Selenium not installed. Installing now...")
        import subprocess
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'selenium'])
            print("✓ Selenium installed successfully")
        except Exception as e:
            print(f"✗ Failed to install Selenium: {e}")
            return None, None
    
    try:
        from selenium import webdriver
        from selenium.webdriver.common.by import By
        from selenium.webdriver.chrome.options import Options
    except ImportError as e:
        print(f"✗ Failed to import Selenium: {e}")
        return None, None
    
    print("\n🌐 Opening browser to fetch image...")
    print("   (A browser window will open briefly)")
    
    chrome_options = Options()
    chrome_options.add_argument('--headless=new')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36')
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
    except Exception as e:
        print(f"\n⚠ Chrome WebDriver not found. Trying with visible browser...")
        chrome_options = Options()
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        try:
            driver = webdriver.Chrome(options=chrome_options)
        except Exception as e2:
            print(f"\n✗ Could not start Chrome browser: {e2}")
            print("\nPlease install ChromeDriver:")
            print("  Windows: choco install chromedriver")
            print("  Mac: brew install chromedriver")
            print("  Or download from: https://chromedriver.chromium.org/")
            return None, None
    
    try:
        print(f"   Loading {url}...")
        driver.get(url)
        
        time.sleep(3)
        
        price = None
        price_selectors = [
            '[class*="price"]',
            '[data-testid*="price"]',
            '[itemprop="price"]',
            'span[class*="Price"]',
            'div[class*="price"]'
        ]
        
        for selector in price_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    text = element.text.strip()
                    if text and ('$' in text or '£' in text or '€' in text):
                        price = text
                        print(f"   Found price: {price}")
                        break
                if price:
                    break
            except:
                continue
        
        img_element = None
        
        selectors = [
            'meta[property="og:image"]',
            'img[class*="product"]',
            'img[class*="Product"]',
            'img[class*="item"]',
            'img[class*="main"]',
            'picture img',
            'div[class*="image"] img',
            'div[class*="Image"] img'
        ]
        
        for selector in selectors:
            try:
                if selector.startswith('meta'):
                    element = driver.find_element(By.CSS_SELECTOR, selector)
                    img_url = element.get_attribute('content')
                    if img_url:
                        print(f"   Found image via {selector}")
                        response = requests.get(img_url) if HAS_REQUESTS else None
                        if response:
                            driver.quit()
                            return Image.open(io.BytesIO(response.content)), price
                else:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        src = element.get_attribute('src') or element.get_attribute('data-src')
                        if src and ('http' in src) and not ('icon' in src.lower() or 'logo' in src.lower()):
                            print(f"   Found image via {selector}")
                            img_url = src
                            response = requests.get(img_url) if HAS_REQUESTS else None
                            if response:
                                driver.quit()
                                return Image.open(io.BytesIO(response.content)), price
            except Exception as e:
                continue
        
        print("   Taking screenshot of page as fallback...")
        screenshot = driver.get_screenshot_as_png()
        driver.quit()
        
        return Image.open(io.BytesIO(screenshot)), price
        
    except Exception as e:
        print(f"   ✗ Browser error: {e}")
        driver.quit()
        return None, None

def fetch_image_from_depop(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Cache-Control': 'max-age=0'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
    except Exception as e:
        print(f"   Direct request failed: {e}")
        print("   Falling back to browser method...")
        return fetch_image_with_browser(url)
    
    import json

    soup = BeautifulSoup(response.content, 'html.parser')
    
    img_url = None
    price = None

    next_data_tag = soup.find('script', {'id': '__NEXT_DATA__'})
    if next_data_tag:
        try:
            next_data = json.loads(next_data_tag.string)
            product = (
                next_data.get('props', {})
                         .get('pageProps', {})
                         .get('productState', {})
                         .get('product', {})
            )
            
            # Use discountedPrice if present, otherwise fall back to priceAmount
            discounted = product.get('discountedPrice', {})
            original = product.get('priceAmount') or product.get('price', {}).get('priceAmount')
            
            amount = discounted.get('priceAmount') if discounted else None
            currency_code = discounted.get('currencyCode') if discounted else None
            
            if not amount:
                amount = original
                currency_code = product.get('currencyCode') or product.get('price', {}).get('currencyCode', 'USD')
            
            if amount:
                price = f"${float(amount):.2f}" if currency_code == 'USD' else f"{float(amount):.2f} {currency_code}"
        except Exception:
            pass
    
    if not price:
        price_meta = soup.find('meta', property='product:price:amount')
        if price_meta and price_meta.get('content'):
            currency_meta = soup.find('meta', property='product:price:currency')
            currency = currency_meta.get('content', 'USD') if currency_meta else 'USD'
            price = f"${price_meta['content']}" if currency == 'USD' else f"{price_meta['content']} {currency}"
    
    og_image = soup.find('meta', property='og:image')
    if og_image and og_image.get('content'):
        img_url = og_image['content']
    
    if not img_url:
        img_tag = soup.find('img', {'class': lambda x: x and 'product' in x.lower()})
        if img_tag:
            img_url = img_tag.get('src') or img_tag.get('data-src')
    
    if not img_url:
        all_imgs = soup.find_all('img')
        for img in all_imgs:
            src = img.get('src') or img.get('data-src')
            if src and ('product' in src.lower() or 'item' in src.lower()):
                img_url = src
                break
    
    if not img_url:
        raise ValueError("Could not find product image on page")
    
    if not img_url.startswith('http'):
        parsed = urlparse(url)
        img_url = f"{parsed.scheme}://{parsed.netloc}{img_url}"
    
    img_response = requests.get(img_url, headers=headers, timeout=10)
    img_response.raise_for_status()
    
    return Image.open(io.BytesIO(img_response.content)), price

def _parse_ebay_price(soup):
    import re
    lines = [l.strip() for l in soup.get_text(separator='\n').splitlines() if l.strip()]

    # "Item price" label appears in eBay's price breakdown, followed by the clean price
    for i, line in enumerate(lines):
        if line.lower() == 'item price' and i + 1 < len(lines):
            m = re.search(r'[A-Z]{0,2}\s*\$\s*([\d,]+\.?\d*)', lines[i + 1])
            if m:
                amount = float(m.group(1).replace(',', ''))
                if amount > 0:
                    return f"${amount:.2f}"

    # Fallback: first line that is solely a price value e.g. "US $58.74"
    price_only = re.compile(r'^(?:[A-Z]{2}\s*)?\$([\d,]+\.\d{2})$')
    for line in lines:
        m = price_only.match(line)
        if m:
            amount = float(m.group(1).replace(',', ''))
            if amount > 0:
                return f"${amount:.2f}"

    return None

def fetch_image_from_ebay(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
    except Exception as e:
        print(f"   Direct request failed: {e}")
        print("   Falling back to browser method...")
        return fetch_image_with_browser(url)
    
    soup = BeautifulSoup(response.content, 'html.parser')
    
    price = _parse_ebay_price(soup)

    img_url = None
    
    og_image = soup.find('meta', property='og:image')
    if og_image and og_image.get('content'):
        img_url = og_image['content']
    
    if not img_url:
        img_div = soup.find('div', {'class': lambda x: x and 'image' in x.lower()})
        if img_div:
            img_tag = img_div.find('img')
            if img_tag:
                img_url = img_tag.get('src') or img_tag.get('data-src')
    
    if not img_url:
        raise ValueError("Could not find product image on page")
    
    img_response = requests.get(img_url, headers=headers, timeout=10)
    img_response.raise_for_status()
    
    return Image.open(io.BytesIO(img_response.content)), price

def fetch_image_from_poshmark(url):
    # Poshmark is fully JS-rendered — static requests return an empty shell.
    # Use Selenium and parse the __NEXT_DATA__ / window.__STATE__ JSON blob.
    import json
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    chrome_options = Options()
    chrome_options.add_argument('--headless=new')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36')

    driver = webdriver.Chrome(options=chrome_options)
    try:
        driver.get(url)
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, 'body'))
        )
        soup = BeautifulSoup(driver.page_source, 'html.parser')
    finally:
        driver.quit()

    price   = None
    img_url = None

    # Poshmark embeds all listing data in a <script id="__NEXT_DATA__"> JSON blob
    next_data_tag = soup.find('script', {'id': '__NEXT_DATA__'})
    if next_data_tag:
        try:
            data    = json.loads(next_data_tag.string)
            listing = (
                data.get('props', {})
                    .get('pageProps', {})
                    .get('listingData', {})
                    .get('listing', {})
            )
            price_cents = listing.get('price_amount', {}).get('val')
            if price_cents is not None:
                price = f"${int(price_cents) / 100:.2f}"

            pictures = listing.get('pictures', [])
            if pictures:
                img_url = pictures[0].get('url_fullsize') or pictures[0].get('url')
        except Exception:
            pass

    # Fallback: og meta tags populated after JS renders
    if not price:
        price_meta = soup.find('meta', property='product:price:amount')
        if price_meta and price_meta.get('content'):
            try:
                amount = float(price_meta['content'])
                currency_meta = soup.find('meta', property='product:price:currency')
                currency = currency_meta.get('content', 'USD') if currency_meta else 'USD'
                price = f"${amount:.2f}" if currency == 'USD' else f"{amount:.2f} {currency}"
            except (ValueError, TypeError):
                pass

    if not img_url:
        og_image = soup.find('meta', property='og:image')
        if og_image and og_image.get('content'):
            img_url = og_image['content']

    if not img_url:
        raise ValueError("Could not find product image on Poshmark listing")

    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    img_response = requests.get(img_url, headers=headers, timeout=10)
    img_response.raise_for_status()
    return Image.open(io.BytesIO(img_response.content)), price

def fetch_image_from_pinterest(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
    }

    response = requests.get(url, headers=headers, timeout=15)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, 'html.parser')

    # Destination URL — Pinterest stores this in og:see_also or the canonical link tag
    destination_url = None
    for tag in soup.find_all('meta'):
        prop = tag.get('property', '') or tag.get('name', '')
        if prop in ('og:see_also', 'pinterest:source_url'):
            destination_url = tag.get('content')
            break

    if not destination_url:
        # Fall back: look for the outbound link in JSON-LD or any <a> pointing off-site
        import json, re
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                data = json.loads(script.string)
                if isinstance(data, dict):
                    destination_url = data.get('url') or data.get('mainEntityOfPage', {}).get('@id')
                    if destination_url and 'pinterest.com' not in destination_url:
                        break
                    else:
                        destination_url = None
            except Exception:
                pass

    if not destination_url:
        # Last resort: any href that goes to a non-Pinterest domain
        for a in soup.find_all('a', href=True):
            href = a['href']
            if href.startswith('http') and 'pinterest.com' not in href:
                destination_url = href
                break

    if not destination_url:
        raise ValueError("Could not find destination URL from Pinterest pin")

    print(f"   Destination URL: {destination_url}")

    import re

    # Price — try Pinterest's product data first, then fall through to destination site
    price = None
    price_match = re.search(r'[$£€]([\d,]+\.\d{2})', soup.get_text())
    if price_match:
        symbol = price_match.group(0)[0]
        amount = float(price_match.group(1).replace(',', ''))
        price = f"{symbol}{amount:.2f}"

    if not price:
        print("   No price on Pinterest pin, fetching from destination...")
        try:
            _, price = fetch_image_from_url(destination_url)
        except Exception:
            pass

    # Image — use the highest-res pinimg URL available
    img_url = None
    og_image = soup.find('meta', property='og:image')
    if og_image and og_image.get('content'):
        img_url = og_image['content']
        # Upgrade to full resolution: replace /236x/, /474x/, /736x/ with /originals/
        img_url = re.sub(r'/\d+x\d*/', '/originals/', img_url)
        img_url = re.sub(r'/736x/', '/originals/', img_url)

    if not img_url:
        raise ValueError("Could not find image in Pinterest pin")

    img_response = requests.get(img_url, headers=headers, timeout=10)
    if img_response.status_code != 200:
        # Fall back to the non-upgraded URL
        og_image = soup.find('meta', property='og:image')
        img_url = og_image['content']
        img_response = requests.get(img_url, headers=headers, timeout=10)
    img_response.raise_for_status()

    return Image.open(io.BytesIO(img_response.content)), price, destination_url


def fetch_image_from_etsy(url):
    # Etsy uses Cloudflare bot protection that blocks all automated browsers.
    # Raise immediately with clear instructions rather than wasting time failing.
    raise ValueError(
        "Etsy blocks automated scraping via Cloudflare.\n\n"
        "To use an Etsy listing:\n"
        "  1. Open the listing in your browser\n"
        "  2. Right-click the main product image and save it\n"
        f" 3. Run: python create_instagram_post.py <saved_image.jpg> \"{url}\""
    )


def fetch_image_from_mercari(url):
    # Mercari is JS-rendered and returns 403 to plain requests.
    # After Selenium renders the page, product data lives in a __NEXT_DATA__ JSON blob.
    import json
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    chrome_options = Options()
    chrome_options.add_argument('--headless=new')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36')

    driver = webdriver.Chrome(options=chrome_options)
    try:
        driver.get(url)
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, 'body'))
        )
        soup = BeautifulSoup(driver.page_source, 'html.parser')
    finally:
        driver.quit()

    price   = None
    img_url = None

    next_data_tag = soup.find('script', {'id': '__NEXT_DATA__'})
    if next_data_tag:
        try:
            data        = json.loads(next_data_tag.string)
            server_state = data.get('props', {}).get('pageProps', {}).get('serverState', {})

            # Key is "ItemDetail:<item_id>"
            item_detail = next(
                (v for k, v in server_state.items() if k.startswith('ItemDetail:')),
                {}
            )
            price_val = item_detail.get('price')
            if price_val is not None:
                price = f"${float(price_val) / 100:.2f}"

            photos = item_detail.get('photos', [])
            if photos:
                img_url = photos[0].get('imageUrl') or photos[0].get('thumbnail')
        except Exception:
            pass

    if not price:
        price_meta = soup.find('meta', property='product:price:amount')
        if price_meta and price_meta.get('content'):
            try:
                amount = float(price_meta['content'])
                currency_meta = soup.find('meta', property='product:price:currency')
                currency = currency_meta.get('content', 'USD') if currency_meta else 'USD'
                price = f"${amount:.2f}" if currency == 'USD' else f"{amount:.2f} {currency}"
            except (ValueError, TypeError):
                pass

    if not img_url:
        # og:image has generic placeholders first — skip them and find the product image
        for tag in soup.find_all('meta', property='og:image'):
            candidate = tag.get('content', '')
            if 'mercdn.net/photos/' in candidate:
                img_url = candidate
                break

    if not img_url:
        raise ValueError("Could not find product image on Mercari listing")

    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    img_response = requests.get(img_url, headers=headers, timeout=10)
    img_response.raise_for_status()
    return Image.open(io.BytesIO(img_response.content)), price


def fetch_image_from_url(url):
    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    
    if 'depop.com' in domain:
        return fetch_image_from_depop(url)
    elif 'ebay.com' in domain:
        return fetch_image_from_ebay(url)
    elif 'poshmark.com' in domain:
        return fetch_image_from_poshmark(url)
    elif 'etsy.com' in domain:
        return fetch_image_from_etsy(url)
    elif 'pinterest.com' in domain or 'pin.it' in domain:
        return fetch_image_from_pinterest(url)
    elif 'mercari.com' in domain:
        return fetch_image_from_mercari(url)
    else:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        try:
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
        except Exception as e:
            print(f"   Direct request failed: {e}")
            print("   Falling back to browser method...")
            return fetch_image_with_browser(url)
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        price = None
        
        discounted_price = soup.find(['span', 'div', 'p'], {'aria-label': 'Discounted price'})
        if discounted_price:
            price = discounted_price.get_text(strip=True)
        
        if not price:
            sale_price = soup.find(['span', 'div'], {'class': lambda x: x and 'sale' in x.lower()})
            if sale_price:
                text = sale_price.get_text(strip=True)
                if '$' in text or '£' in text or '€' in text:
                    price = text
        
        if not price:
            price_meta = soup.find('meta', property='product:price:amount')
            if price_meta and price_meta.get('content'):
                price = price_meta['content']
                currency_meta = soup.find('meta', property='product:price:currency')
                currency = currency_meta.get('content', 'USD') if currency_meta else 'USD'
                price = f"${price}" if currency == 'USD' else f"{price} {currency}"
        
        if not price:
            price_elements = soup.find_all(['span', 'div'], {'class': lambda x: x and 'price' in x.lower()})
            prices_found = []
            for elem in price_elements:
                text = elem.get_text(strip=True)
                if '$' in text or '£' in text or '€' in text:
                    try:
                        price_value = float(''.join(filter(lambda c: c.isdigit() or c == '.', text)))
                        prices_found.append((price_value, text))
                    except:
                        pass
            
            if prices_found:
                prices_found.sort(key=lambda x: x[0])
                price = prices_found[0][1]
        
        og_image = soup.find('meta', property='og:image')
        
        if og_image and og_image.get('content'):
            img_url = og_image['content']
            img_response = requests.get(img_url, headers=headers, timeout=10)
            img_response.raise_for_status()
            return Image.open(io.BytesIO(img_response.content)), price
        
        raise ValueError(f"Unsupported site or could not find image: {domain}")

def format_for_instagram(img, bg_color):
    width, height = img.size

    if width > height:
        new_size = width
        canvas = Image.new('RGB', (new_size, new_size), bg_color)
        paste_y = (new_size - height) // 2
        canvas.paste(img, (0, paste_y))
    else:
        new_size = height
        canvas = Image.new('RGB', (new_size, new_size), bg_color)
        paste_x = (new_size - width) // 2
        canvas.paste(img, (paste_x, 0))

    instagram_size = 1080
    canvas = canvas.resize((instagram_size, instagram_size), Image.Resampling.LANCZOS)

    return canvas

def get_dominant_color(img):
    img_small = img.resize((150, 150)).convert('RGB')
    raw = img_small.tobytes()
    pixels = [(raw[i], raw[i+1], raw[i+2]) for i in range(0, len(raw), 3)]
    
    color_counts = {}
    for r, g, b in pixels:
        if r > 240 and g > 240 and b > 240:
            continue
        if r < 15 and g < 15 and b < 15:
            continue
        
        key = (r // 30 * 30, g // 30 * 30, b // 30 * 30)
        color_counts[key] = color_counts.get(key, 0) + 1
    
    if not color_counts:
        return (100, 100, 100)
    
    dominant = max(color_counts.items(), key=lambda x: x[1])[0]
    
    r, g, b = dominant
    brightness = (r * 299 + g * 587 + b * 114) / 1000
    if brightness < 80:
        factor = 80 / brightness if brightness > 0 else 2
        r = min(255, int(r * factor))
        g = min(255, int(g * factor))
        b = min(255, int(b * factor))
    
    return (r, g, b)

def create_rounded_rectangle(size, radius, fill_color, border_color, border_width):
    img = Image.new('RGBA', size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    width, height = size
    
    draw.rounded_rectangle(
        [(0, 0), (width, height)],
        radius=radius,
        fill=fill_color,
        outline=border_color,
        width=border_width
    )
    
    return img

def _sanitize_price(price):
    """Extract a clean price string (e.g. '$58.74') or return None if unparseable.
    Accepts formats: '$49', '49', '49.99', '$49.99', '£49', etc.
    Plain numbers default to USD.
    """
    import re
    if not price:
        return None
    price = price.strip()

    # Try symbol + amount first
    m = re.search(r'([$£€])([\d,]+\.?\d*)', price)
    if m:
        symbol = m.group(1)
        amount = float(m.group(2).replace(',', ''))
        return f"{symbol}{amount:.2f}"

    # Plain number with no symbol — assume USD
    m = re.search(r'^[\d,]+\.?\d*$', price)
    if m:
        amount = float(price.replace(',', ''))
        return f"${amount:.2f}"

    return None

def add_price_overlay(img, price, dominant_color):
    price = _sanitize_price(price)
    if not price:
        return img
    
    img_rgba = img.convert('RGBA')
    
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 48)
        small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 36)
    except:
        try:
            font = ImageFont.truetype("arial.ttf", 48)
            small_font = ImageFont.truetype("arial.ttf", 36)
        except:
            font = ImageFont.load_default()
            small_font = font
    
    temp_draw = ImageDraw.Draw(img_rgba)
    bbox = temp_draw.textbbox((0, 0), price, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    padding_h = 30
    padding_v = 20
    border_width = 4
    corner_radius = 15
    
    box_width = text_width + 2 * padding_h + 2 * border_width
    box_height = text_height + 2 * padding_v + 2 * border_width
    
    bg_box = create_rounded_rectangle(
        (box_width, box_height),
        corner_radius,
        (255, 255, 255, 245),
        dominant_color + (255,),
        border_width
    )
    
    margin = 35
    x = margin
    y = img_rgba.height - box_height - margin
    
    img_rgba.paste(bg_box, (x, y), bg_box)
    
    draw = ImageDraw.Draw(img_rgba)
    text_x = x + padding_h + border_width
    text_y = y + padding_v + border_width
    
    draw.text((text_x, text_y), price, fill=dominant_color + (255,), font=font)
    
    return img_rgba

SITE_LOGOS = {
    'depop.com':    'logos/depop.png',
    'depop.app.link':    'logos/depop.png',
    'ebay.com':     'logos/ebay.png',
    'poshmark.com': 'logos/poshmark.png',
    'etsy.com':     'logos/etsy.png',
    'pinterest.com':'logos/pinterest.png',
    'vinted.com':   'logos/vinted.png',
    'grailed.com':  'logos/grailed.png',
    'mercari.com':  'logos/mercari.png',
    'agedivy.com':  'logos/agedivy.png',
}
LOGO_DEFAULT = 'logos/default.png'
LOGO_HEIGHT  = 60  # fixed height in pixels on the 1080px canvas; width scales naturally


def _get_logo_path(url):
    import os
    domain = urlparse(url).netloc.lower()
    for key, path in SITE_LOGOS.items():
        if key in domain:
            return path if os.path.exists(path) else LOGO_DEFAULT
    return LOGO_DEFAULT


def add_logo_overlay(img, url):
    import os
    logo_path = _get_logo_path(url)
    if not os.path.exists(logo_path):
        return img

    logo = Image.open(logo_path).convert('RGBA')
    orig_w, orig_h = logo.size
    logo_w = max(1, int(orig_w * LOGO_HEIGHT / orig_h))
    logo = logo.resize((logo_w, LOGO_HEIGHT), Image.Resampling.LANCZOS)

    img_rgba = img.convert('RGBA')
    margin   = 35
    x        = (img_rgba.width - logo_w) // 2
    y        = img_rgba.height - LOGO_HEIGHT - margin
    img_rgba.paste(logo, (x, y), logo)

    return img_rgba.convert('RGB')


# Domains that are app-link redirectors — must be resolved to find the real web URL
APP_LINK_DOMAINS = (
    'app.link',       # Branch.io (used by Depop, many others)
    'app.adjust.com',
    'go.onelink.me',
    'click.etsy.com',
    'etsy.app.link',
    'l.instagram.com',
    'out.reddit.com',
)


def _resolve_app_link(url):
    """Follow redirect chain with a desktop UA to get the final web URL."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    }
    try:
        r = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
        final = r.url
        # Reject if we landed back on an app-link domain or got no meaningful redirect
        if any(d in urlparse(final).netloc for d in APP_LINK_DOMAINS):
            return url
        return final
    except Exception:
        return url


def _canonicalize_url(url):
    """
    Normalize a URL to a clean desktop web link for QR codes.
    Resolves app/deep-link redirectors, strips tracking params and mobile subdomains
    so Safari opens the browser instead of the app.
    """
    import re
    from urllib.parse import parse_qs, urlencode

    # Resolve app-link shorteners / universal link redirectors first
    parsed_check = urlparse(url)
    if any(d in parsed_check.netloc for d in APP_LINK_DOMAINS):
        print(f"   Resolving app link: {url}")
        url = _resolve_app_link(url)
        print(f"   Resolved to: {url}")

    # Replace non-http schemes (depop://, etc.) with https
    if not url.startswith('http'):
        url = re.sub(r'^[a-zA-Z][a-zA-Z0-9+\-.]*://', 'https://', url)

    parsed = urlparse(url)
    scheme = 'https'
    netloc = re.sub(r'^m\.', '', parsed.netloc)  # strip mobile subdomain
    domain = netloc.lower()
    path   = parsed.path

    STRIP_PARAMS = {
        'utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term',
        'ref', 'referrer', 'source', 'share', 'shareable_code',
        'norover', '_trkparms', '_trksid', 'ssPageName',
        'fbclid', 'gclid', 'msclkid',
    }
    params       = parse_qs(parsed.query, keep_blank_values=False)
    clean_params = {k: v for k, v in params.items() if k not in STRIP_PARAMS}

    if 'depop.com' in domain:
        netloc = 'www.depop.com'; clean_params = {}
    elif 'ebay.com' in domain:
        netloc = 'www.ebay.com'; clean_params = {}
    elif 'poshmark.com' in domain:
        netloc = 'poshmark.com'; clean_params = {}
    elif 'etsy.com' in domain:
        # Use etsy.com without www — iOS Universal Links only match www.etsy.com,
        # so this forces Safari to open the browser instead of the app.
        netloc = 'etsy.com'; clean_params = {}
    elif 'mercari.com' in domain:
        netloc = 'www.mercari.com'; clean_params = {}
    elif 'pinterest.com' in domain or 'pin.it' in domain:
        clean_params = {}
    elif 'grailed.com' in domain:
        netloc = 'www.grailed.com'; clean_params = {}
    elif 'vinted.com' in domain:
        clean_params = {}

    query = urlencode(clean_params, doseq=True)
    return parsed._replace(scheme=scheme, netloc=netloc, path=path, query=query, fragment='').geturl()


def add_qr_code_overlay(img, url):
    url = _canonicalize_url(url)
    dominant_color = get_dominant_color(img)

    qr_size = 200
    qr_img = create_qr_code_image(url, qr_size)
    
    padding = 35
    inner_padding = 20
    text_space = 50
    border_width = 4
    corner_radius = 20
    
    total_width = qr_size + 2 * inner_padding + 2 * border_width
    total_height = qr_size + 2 * inner_padding + text_space + 2 * border_width
    
    bg_img = create_rounded_rectangle(
        (total_width, total_height),
        corner_radius,
        (255, 255, 255, 245),
        dominant_color + (255,),
        border_width
    )
    
    qr_mask = Image.new('L', qr_img.size, 0)
    qr_mask_draw = ImageDraw.Draw(qr_mask)
    qr_mask_draw.rounded_rectangle(
        [(0, 0), qr_img.size],
        radius=12,
        fill=255
    )
    
    qr_rounded = Image.new('RGBA', qr_img.size, (255, 255, 255, 0))
    qr_rounded.paste(qr_img, (0, 0), qr_mask)
    
    qr_x = border_width + inner_padding
    qr_y = border_width + inner_padding + text_space
    bg_img.paste(qr_rounded, (qr_x, qr_y), qr_rounded)
    
    draw = ImageDraw.Draw(bg_img)
    
    text = "Screenshot to visit"
    
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 18)
    except:
        try:
            font = ImageFont.truetype("arial.ttf", 18)
        except:
            font = ImageFont.load_default()
    
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_x = (total_width - text_width) // 2
    text_y = border_width + 15
    
    draw.text((text_x, text_y), text, fill=dominant_color + (255,), font=font)
    
    img_rgba = img.convert('RGBA')
    
    x = img_rgba.width - total_width - padding
    y = img_rgba.height - total_height - padding
    
    img_rgba.paste(bg_img, (x, y), bg_img)
    
    return img_rgba.convert('RGB')

def _prompt_manual_fix(original_url, index):
    """On failure, ask the user if they want to supply image/price manually."""
    print(f"\n  Manual fix? (Y/N): ", end='', flush=True)
    answer = input().strip().lower()
    if answer != 'y':
        return None

    print(f"  Image URL (direct link to the product photo): ", end='', flush=True)
    img_url = input().strip()
    print(f"  Price (e.g. $24.99, or leave blank to skip): ", end='', flush=True)
    price_raw = input().strip() or None

    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        img_response = requests.get(img_url, headers=headers, timeout=15)
        img_response.raise_for_status()
        product_img = Image.open(io.BytesIO(img_response.content))
    except Exception as e:
        print(f"  ✗ Could not load image: {e}")
        return None

    price = _sanitize_price(price_raw) if price_raw else None

    dominant_color = get_dominant_color(product_img)
    instagram_img  = format_for_instagram(product_img, dominant_color)
    if price:
        instagram_img = add_price_overlay(instagram_img, price, dominant_color)
    instagram_img = add_logo_overlay(instagram_img, original_url)
    # QR code always points to the original URL that failed
    final_img = add_qr_code_overlay(instagram_img, original_url)

    import os
    os.makedirs('output', exist_ok=True)
    suffix = f"_{index}" if index is not None else ""
    output_filename = f"output/instagram_post{suffix}.jpg"
    final_img.save(output_filename, 'JPEG', quality=95)
    print(f"  ✓ Saved: {output_filename}")
    return output_filename


def _save_post(product_img, price, url, index):
    """Shared final steps: color → format → overlays → save."""
    import os
    dominant_color = get_dominant_color(product_img)
    instagram_img  = format_for_instagram(product_img, dominant_color)
    if price:
        instagram_img = add_price_overlay(instagram_img, price, dominant_color)
    instagram_img = add_logo_overlay(instagram_img, url)
    final_img     = add_qr_code_overlay(instagram_img, url)

    os.makedirs('output', exist_ok=True)
    suffix = f"_{index}" if index is not None else ""
    output_filename = f"output/instagram_post{suffix}.jpg"
    final_img.save(output_filename, 'JPEG', quality=95)
    return output_filename


def process_single(url, image_path=None, index=None):
    """Process one URL/image into an instagram post. Returns output filename or None on failure."""
    label = f"[{index}] " if index is not None else ""
    price = None

    try:
        if image_path:
            print(f"\n{label}[1/5] Loading local image: {image_path}")
            try:
                product_img = Image.open(image_path)
            except Exception as e:
                print(f"✗ Error loading image file: {e}")
                return None
        else:
            print(f"\n{label}[1/5] Fetching product image and price from URL...")
            result = fetch_image_from_url(url)
            if len(result) == 3:
                product_img, price, url = result
                print(f"   Pin destination: {url}")
            else:
                product_img, price = result
            if price:
                print(f"   Found price: {price}")

        print(f"{label}[2/5] Extracting dominant color...")
        print(f"{label}[3/5] Formatting for Instagram (1:1 aspect ratio)...")
        print(f"{label}[4/5] Adding overlays...")
        output_filename = _save_post(product_img, price, url, index)
        print(f"{label}[5/5] Saving as '{output_filename}'...")

        print(f"\n✓ {label}Saved: {output_filename}")
        if price:
            print(f"  - Price: {price}")
        print(f"  - QR code links to: {url}")
        return output_filename

    except requests.exceptions.RequestException as e:
        print(f"\n✗ {label}Network error: {e}")
        print("  Trying browser automation...")
        try:
            product_img, price = fetch_image_with_browser(url)
            if product_img:
                output_filename = _save_post(product_img, price, url, index)
                print(f"\n✓ {label}Saved: {output_filename}")
                return output_filename
        except Exception:
            pass
        print(f"  ✗ {label}Browser automation also failed.")
        return _prompt_manual_fix(url, index)
    except ValueError as e:
        print(f"\n✗ {label}Error: {e}")
        return _prompt_manual_fix(url, index)
    except Exception as e:
        print(f"\n✗ {label}Unexpected error: {e}")
        return _prompt_manual_fix(url, index)


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python create_instagram_post.py <url>")
        print("  python create_instagram_post.py <image.jpg> <url>")
        print("  python create_instagram_post.py <links.txt>")
        print("\nExamples:")
        print("  python create_instagram_post.py https://www.depop.com/products/...")
        print("  python create_instagram_post.py product.jpg https://depop.com/...")
        print("  python create_instagram_post.py links.txt")
        print("\nSupported sites: Depop, eBay, Poshmark, Pinterest, and sites with og:image meta tags")
        sys.exit(1)

    # txt file batch mode
    arg = sys.argv[1]
    if arg.endswith('.txt') and not arg.startswith('http'):
        try:
            with open(arg) as f:
                urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        except FileNotFoundError:
            print(f"✗ File not found: {arg}")
            sys.exit(1)

        if not urls:
            print("✗ No URLs found in file")
            sys.exit(1)

        print(f"Processing {len(urls)} URLs from {arg}...")
        succeeded, failed = [], []
        for i, url in enumerate(urls, 1):
            result = process_single(url, index=i)
            (succeeded if result else failed).append(url)

        print(f"\n{'='*50}")
        print(f"Batch complete: {len(succeeded)}/{len(urls)} succeeded")
        if failed:
            print(f"Failed ({len(failed)}):")
            for u in failed:
                print(f"  - {u}")
        sys.exit(0 if not failed else 1)

    # Single image + url mode
    if len(sys.argv) == 3:
        image_path, url = sys.argv[1], sys.argv[2]
        try:
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                print("Error: Invalid URL provided")
                sys.exit(1)
        except Exception as e:
            print(f"Error: Invalid URL - {e}")
            sys.exit(1)
        result = process_single(url, image_path=image_path)
        sys.exit(0 if result else 1)

    # Single URL mode
    url = sys.argv[1]
    try:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            print("Error: Invalid URL provided")
            sys.exit(1)
    except Exception as e:
        print(f"Error: Invalid URL - {e}")
        sys.exit(1)

    result = process_single(url)
    sys.exit(0 if result else 1)


if __name__ == "__main__":
    main()