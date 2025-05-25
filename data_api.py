# data_api.py
import requests
from constants import API_KEY, CORP_CODE_URL, FS_URL

# Fetch financials for a given corp_code and year

def fetch_financials(corp_code, year):
    params = {
        'crtfc_key': API_KEY,
        'corp_code': corp_code,
        'bsns_year': year,
        'reprt_code': '11011',  # 사업보고서(연간)
    }
    try:
        r = requests.get(FS_URL, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
        if data.get('status') != '000':
            return {"매출액": 0, "당기순이익": 0}
        result = {"매출액": 0, "당기순이익": 0}
        for fin in data.get('list', []):
            account_nm = fin.get('account_nm')
            amount = fin.get('thstrm_amount')
            if account_nm in ['수익(매출액)', '매출액', '영업수익']:
                try:
                    result['매출액'] = int(amount.replace(',', ''))
                except Exception:
                    result['매출액'] = 0
            if account_nm in ['당기순이익', '순이익', 'Net Income', 'Net profit']:
                try:
                    result['당기순이익'] = int(amount.replace(',', ''))
                except Exception:
                    result['당기순이익'] = 0
        return result
    except Exception:
        return {"매출액": 0, "당기순이익": 0}

# Fetch and cache corp code map from DART

def get_corp_map():
    import zipfile, io
    from xml.etree import ElementTree
    resp = requests.get(CORP_CODE_URL, params={'crtfc_key': API_KEY}, timeout=30)
    with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
        xml_data = z.read(z.namelist()[0])
    root = ElementTree.fromstring(xml_data)
    return {elem.find('stock_code').text: elem.find('corp_code').text
            for elem in root.findall('list') if elem.find('stock_code').text} 