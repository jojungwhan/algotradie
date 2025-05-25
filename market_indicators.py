# market_indicators.py
import yfinance as yf
import requests
from bs4 import BeautifulSoup

def get_vkospi_naver():
    try:
        url = 'https://finance.naver.com/sise/sise_index_day.naver?code=VKSPI'
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
        }
        resp = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(resp.text, 'html.parser')
        table = soup.find('table', class_='type_1')
        if not table:
            html_sample = soup.prettify()[:2000]
            return None, f'Naver: Table not found, page sample: {html_sample}'
        rows = table.find_all('tr')
        debug_rows = []
        candidate_values = []
        for row in rows:
            cols = row.find_all('td')
            if len(cols) >= 2:
                val = cols[1].text.strip().replace(',', '')
                debug_rows.append(val)
                if val and val.replace('.', '', 1).isdigit():
                    fval = float(val)
                    candidate_values.append(fval)
        # Find the first non-zero value
        for fval in candidate_values:
            if fval != 0:
                return fval, f'Naver: Success, parsed value {fval}, debug rows: {debug_rows[:10]}'
        table_html = table.prettify()[:2000]
        return None, f'Naver: No valid non-zero value found, debug rows: {debug_rows[:10]}, table sample: {table_html}'
    except Exception as e:
        return None, f'Naver: Error {e}'

def get_vkospi_daum():
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        url = 'https://finance.daum.net/domestic/index?code=VKSPI'
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--disable-gpu')
        driver = webdriver.Chrome(options=options)
        driver.get(url)
        import time
        time.sleep(3)  # Wait for JS to load
        page_source = driver.page_source
        driver.quit()
        soup = BeautifulSoup(page_source, 'html.parser')
        # Try to find the VKOSPI value in the rendered page
        debug_text = []
        for span in soup.find_all('span'):
            txt = span.text.strip().replace(',', '')
            debug_text.append(txt)
            if txt.replace('.', '', 1).isdigit() and float(txt) > 0:
                return float(txt), f'Daum: Success, parsed value {txt}, debug spans: {debug_text[:10]}'
        html_sample = soup.prettify()[:2000]
        return None, f'Daum: Could not find value, debug spans: {debug_text[:10]}, html sample: {html_sample}'
    except Exception as e:
        return None, f'Daum: Error {e}'

def get_vkospi_investing():
    try:
        url = 'https://kr.investing.com/indices/kospi-volatility'
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
        }
        resp = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(resp.text, 'html.parser')
        # The main price is usually in a span with id 'last_last' or similar
        price_tag = soup.find('span', id='last_last')
        debug_text = []
        if price_tag:
            val = price_tag.text.strip().replace(',', '')
            debug_text.append(val)
            if val.replace('.', '', 1).isdigit():
                return float(val), f'Investing: Success, parsed value {val}, debug: {debug_text}'
        # Fallback: try to find any large number in span tags
        for span in soup.find_all('span'):
            txt = span.text.strip().replace(',', '')
            debug_text.append(txt)
            if txt.replace('.', '', 1).isdigit() and float(txt) > 0:
                return float(txt), f'Investing: Fallback, parsed value {txt}, debug: {debug_text[:10]}'
        html_sample = soup.prettify()[:2000]
        return None, f'Investing: Could not find value, debug: {debug_text[:10]}, html sample: {html_sample}'
    except Exception as e:
        return None, f'Investing: Error {e}'

def get_vkospi():
    tickers = ['^VKSPI', 'KOSPI200VI.KS', 'KOSPI200VI']
    debug_msgs = []
    for ticker in tickers:
        try:
            vkospi = yf.Ticker(ticker)
            data = vkospi.history(period='1d')
            if not data.empty:
                latest = data.iloc[-1]
                return float(latest['Close']), f"Success: {ticker}"
            else:
                debug_msgs.append(f"No data for ticker: {ticker}")
        except Exception as e:
            debug_msgs.append(f"Error for ticker {ticker}: {e}")
    # Try Naver as fallback
    naver_val, naver_debug = get_vkospi_naver()
    if naver_val is not None:
        return naver_val, naver_debug
    debug_msgs.append(naver_debug)
    # Try Daum as fallback
    daum_val, daum_debug = get_vkospi_daum()
    if daum_val is not None:
        return daum_val, daum_debug
    debug_msgs.append(daum_debug)
    # Try Investing.com as fallback
    invest_val, invest_debug = get_vkospi_investing()
    if invest_val is not None:
        return invest_val, invest_debug
    debug_msgs.append(invest_debug)
    return None, ' | '.join(debug_msgs)

def get_cnn_fear_greed():
    try:
        # Try macromicro.me aggregator first
        url = 'https://en.macromicro.me/charts/50108/cnn-fear-and-greed'
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
        }
        resp = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(resp.text, 'html.parser')
        debug_text = []
        # Try to find the value in a chart summary or value tag
        for div in soup.find_all('div'):
            txt = div.text.strip()
            debug_text.append(txt)
            # MacroMicro sometimes shows the value as 'Fear & Greed Index: 70' or similar
            if 'Fear & Greed Index' in txt:
                for part in txt.split(':'):
                    part = part.strip()
                    if part.isdigit() and 0 <= int(part) <= 100:
                        return int(part), f'Macromicro: Success, debug divs: {debug_text[:10]}'
            if txt.isdigit() and 0 <= int(txt) <= 100:
                return int(txt), f'Macromicro: Success, debug divs: {debug_text[:10]}'
        html_sample = soup.prettify()[:2000]
        # Fallback to previous methods if not found
        # Try alternative aggregator first (easy to swap URL)
        url = 'https://money.cnn.com/data/fear-and-greed/'
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
        }
        resp = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(resp.text, 'html.parser')
        fg_val = None
        debug_text = []
        for strong in soup.find_all('strong'):
            txt = strong.text.strip()
            debug_text.append(txt)
            if txt.isdigit() and 0 <= int(txt) <= 100:
                fg_val = int(txt)
                break
        if fg_val is not None:
            return fg_val, f'CNN Alt: Success, debug strongs: {debug_text[:10]}'
        # If not found, print a larger sample of the HTML
        html_sample = soup.prettify()[:2000]
        # Try Selenium if available
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            options = Options()
            options.add_argument('--headless')
            options.add_argument('--disable-gpu')
            driver = webdriver.Chrome(options=options)
            driver.get(url)
            page_source = driver.page_source
            driver.quit()
            soup = BeautifulSoup(page_source, 'html.parser')
            debug_text = []
            for strong in soup.find_all('strong'):
                txt = strong.text.strip()
                debug_text.append(txt)
                if txt.isdigit() and 0 <= int(txt) <= 100:
                    fg_val = int(txt)
                    break
            if fg_val is not None:
                return fg_val, f'CNN Selenium: Success, debug strongs: {debug_text[:10]}'
            html_sample = soup.prettify()[:2000]
            return None, f'CNN Selenium: Could not find index value, debug strongs: {debug_text[:10]}, html sample: {html_sample}'
        except Exception as se:
            return None, f'CNN Alt: Could not find index value, debug strongs: {debug_text[:10]}, html sample: {html_sample}, Selenium error: {se}'
    except Exception as e:
        return None, f'Macromicro: Error {e}'

def get_macromicro_iframe():
    # Returns the HTML for embedding the MacroMicro Fear & Greed chart
    return '''<iframe src="https://en.macromicro.me/charts/50108/cnn-fear-and-greed" width="100%" height="400" frameborder="0" scrolling="no"></iframe>'''

def get_us_vix_investing():
    try:
        url = 'https://www.investing.com/indices/volatility-s-p-500'
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
        }
        resp = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(resp.text, 'html.parser')
        price_tag = soup.find('span', id='last_last')
        debug_text = []
        if price_tag:
            val = price_tag.text.strip().replace(',', '')
            debug_text.append(val)
            if val.replace('.', '', 1).isdigit():
                return float(val), f'US VIX Investing: Success, parsed value {val}, debug: {debug_text}'
        # Fallback: try to find any large number in span tags
        for span in soup.find_all('span'):
            txt = span.text.strip().replace(',', '')
            debug_text.append(txt)
            if txt.replace('.', '', 1).isdigit() and float(txt) > 0:
                return float(txt), f'US VIX Investing: Fallback, parsed value {txt}, debug: {debug_text[:10]}'
        html_sample = soup.prettify()[:2000]
        return None, f'US VIX Investing: Could not find value, debug: {debug_text[:10]}, html sample: {html_sample}'
    except Exception as e:
        return None, f'US VIX Investing: Error {e}'

def get_us_vix():
    return get_us_vix_investing() 