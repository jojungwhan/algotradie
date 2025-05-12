import streamlit as st
import pandas as pd
import requests

st.set_page_config(page_title="Korean Companies Revenue Trends", layout="wide")
st.title("Korean Public Companies Revenue Trends (DART API)")

# Load company list
df_companies = pd.read_csv('korean public traded companies.csv', dtype={'종목코드': str})

# Sidebar: Year selection
years = list(range(2015, 2025))
selected_years = st.sidebar.slider('Select year range', min_value=years[0], max_value=years[-1], value=(2020, 2023))

API_KEY = '1d22d31a791581b6ce16099c6e03628b3b876722'
FS_URL = 'https://opendart.fss.or.kr/api/fnlttSinglAcnt.json'

# Sidebar: Company selection
selected_companies = st.sidebar.multiselect(
    'Select companies (by name)',
    options=df_companies['회사명'],
    default=df_companies['회사명'].head(5)
)

# Map stock code to corp code
@st.cache_data
def get_corp_map():
    import zipfile, io
    from xml.etree import ElementTree
    CORP_CODE_URL = 'https://opendart.fss.or.kr/api/corpCode.xml'
    resp = requests.get(CORP_CODE_URL, params={'crtfc_key': API_KEY}, timeout=30)
    with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
        xml_data = z.read(z.namelist()[0])
    root = ElementTree.fromstring(xml_data)
    return {elem.find('stock_code').text: elem.find('corp_code').text
            for elem in root.findall('list') if elem.find('stock_code').text}

corp_map = get_corp_map()

# Prepare data for selected companies and years
results = []
account_nm_set = set()
for company in selected_companies:
    stock_code = df_companies[df_companies['회사명'] == company]['종목코드'].values[0]
    corp_code = corp_map.get(stock_code)
    if not corp_code:
        continue
    for year in range(selected_years[0], selected_years[1]+1):
        params = {
            'crtfc_key': API_KEY,
            'corp_code': corp_code,
            'bsns_year': str(year),
            'reprt_code': '11011'  # 사업보고서
        }
        try:
            r = requests.get(FS_URL, params=params, timeout=30)
            data = r.json()
            if data.get('status') != '000':
                continue
            for fin in data.get('list', []):
                account_nm = fin.get('account_nm')
                account_nm_set.add(account_nm)
                if account_nm in ['수익(매출액)', '매출액', '영업수익']:
                    results.append({
                        '회사명': company,
                        '종목코드': stock_code,
                        '연도': year,
                        '매출액': fin.get('thstrm_amount')
                    })
        except Exception as e:
            continue

# Show revenue trends
df_results = pd.DataFrame(results)
if not df_results.empty:
    st.subheader('Revenue Trends')
    df_pivot = df_results.pivot(index='회사명', columns='연도', values='매출액')
    st.dataframe(df_pivot)
    st.line_chart(df_pivot.T)
else:
    st.info('No revenue data found for the selected companies and years.')

# Show all available account_nm types
st.subheader('Other Types of Information (account_nm) from DART API')
if account_nm_set:
    st.write(sorted(account_nm_set))
else:
    st.info('No account_nm information found for the selected companies and years.') 