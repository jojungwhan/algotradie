import os
import requests
import pandas as pd
from xml.etree import ElementTree
import zipfile
import io

print(f"[INFO] Current working directory: {os.getcwd()}")

# 1) API 키 및 엔드포인트
API_KEY = '1d22d31a791581b6ce16099c6e03628b3b876722'
CORP_CODE_URL = 'https://opendart.fss.or.kr/api/corpCode.xml'
FS_URL = 'https://opendart.fss.or.kr/api/fnlttSinglAcnt.json'

try:
    print("[INFO] Downloading corp code mapping from DART API...")
    resp = requests.get(CORP_CODE_URL, params={'crtfc_key': API_KEY}, timeout=30)
    resp.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
        xml_data = z.read(z.namelist()[0])
    root = ElementTree.fromstring(xml_data)
    corp_map = {elem.find('stock_code').text: elem.find('corp_code').text
                for elem in root.findall('list') if elem.find('stock_code').text}
except Exception as e:
    print(f"[ERROR] Failed to download or parse corp code mapping: {e}")
    exit(1)

# 3) CSV 로드
try:
    print("[INFO] Loading CSV file: korean public traded companies.csv")
    df = pd.read_csv('korean public traded companies.csv', dtype={'종목코드': str})
    df['2024년 매출액(원)'] = None
except FileNotFoundError:
    print("[ERROR] CSV file not found: korean public traded companies.csv")
    exit(1)
except Exception as e:
    print(f"[ERROR] Failed to load CSV: {e}")
    exit(1)

# 4) 기업별 매출 추출
print("[INFO] Fetching revenue data for each company...")
for idx, row in df.iterrows():
    stock_code = row['종목코드']
    corp_code = corp_map.get(stock_code)
    if not corp_code:
        print(f"[WARN] No corp_code found for stock_code: {stock_code}")
        continue

    params = {
        'crtfc_key': API_KEY,
        'corp_code': corp_code,
        'bsns_year': '2023',
        'reprt_code': '11011'  # 1분기(11013), 반기(11012) 등
    }
    try:
        r = requests.get(FS_URL, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
        if data.get('status') != '000':
            print(f"[WARN] API returned error for corp_code: {corp_code} (stock_code: {stock_code}): {data.get('message')}")
            continue
        found = False
        account_names = []
        for fin in data.get('list', []):
            account_nm = fin.get('account_nm')
            account_names.append(account_nm)
            # '수익(매출액)' or similar may be the correct field
            if account_nm in ['수익(매출액)', '매출액', '영업수익']:
                df.at[idx, '2024년 매출액(원)'] = fin.get('thstrm_amount')
                found = True
                break
        if not found:
            print(f"[WARN] No revenue data found for corp_code: {corp_code} (stock_code: {stock_code})")
            print(f"[DEBUG] account_nm values returned: {account_names}")
            print(f"[DEBUG] Full API JSON response: {data}")
    except Exception as e:
        print(f"[ERROR] Failed to fetch or parse financial data for corp_code: {corp_code} (stock_code: {stock_code}): {e}")

# 5) 결과 저장
try:
    print("[INFO] Saving results to CSV: korean_companies_with_revenue_2024.csv")
    df.to_csv('korean_companies_with_revenue_2024.csv', index=False)
    print("완료: korean_companies_with_revenue_2024.csv 생성됨")
except Exception as e:
    print(f"[ERROR] Failed to save CSV file: {e}")
    exit(1) 