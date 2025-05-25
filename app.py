import streamlit as st
import pandas as pd
import requests
import xml.etree.ElementTree as ET
import plotly.graph_objects as go
from st_aggrid import AgGrid, GridOptionsBuilder
import os
import numpy as np
import datetime
import configparser
from fear_greed_screenshot import capture_fear_greed_graph
import streamlit.components.v1 as components

from constants import REVENUE_FIELDS, BENEFIT_TOPICS
from data_api import fetch_financials, get_corp_map
from utils import save_last_csv_path, load_last_csv_path
from data_loader import load_company_data, filter_by_benefit_topics
from market_indicators import get_vkospi, get_us_vix, get_macromicro_iframe

st.set_page_config(page_title="Korean Stocks", layout="wide")
st.markdown('<style>div.block-container {padding-top: 1rem;}</style>', unsafe_allow_html=True)
st.title("Korean Stocks")

API_KEY = '1d22d31a791581b6ce16099c6e03628b3b876722'
CORP_CODE_URL = 'https://opendart.fss.or.kr/api/corpCode.xml'
FS_URL = 'https://opendart.fss.or.kr/api/fnlttSinglAcnt.json'

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
            # Optionally add more fields as needed
        return result
    except Exception:
        return {"매출액": 0, "당기순이익": 0}
    
@st.cache_data
def get_corp_map():
    import zipfile, io
    from xml.etree import ElementTree
    resp = requests.get(CORP_CODE_URL, params={'crtfc_key': API_KEY}, timeout=30)
    with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
        xml_data = z.read(z.namelist()[0])
    root = ElementTree.fromstring(xml_data)
    return {elem.find('stock_code').text: elem.find('corp_code').text
            for elem in root.findall('list') if elem.find('stock_code').text}

corp_map = get_corp_map()

# Load Gemini company info
try:
    df_gemini = pd.read_csv('korean_companies_with_gemini_info_test.csv', encoding='utf-8')
except Exception as e:
    st.warning(f"Could not load Gemini info CSV: {e}")
    df_gemini = pd.DataFrame()

INI_FILE = 'app_settings.ini'
def save_last_csv_path(path):
    config = configparser.ConfigParser()
    config['LAST'] = {'csv_path': path}
    with open(INI_FILE, 'w', encoding='utf-8') as f:
        config.write(f)
def load_last_csv_path():
    if not os.path.exists(INI_FILE):
        return None
    config = configparser.ConfigParser()
    config.read(INI_FILE, encoding='utf-8')
    return config['LAST'].get('csv_path', None) if 'LAST' in config else None

# --- File uploader for main company CSV ---
last_csv_path = load_last_csv_path()
loaded_from_ini = False
uploaded_file = st.sidebar.file_uploader(
    "Select a company CSV file (must include benefit flags)", 
    type=["csv"], 
    help="Upload a CSV file with columns: AI, Robotics, Defense, Environment, Bio, Longevity."
)

df_companies = load_company_data(uploaded_file)

df_companies_full = df_companies.copy()

# --- Benefit Topic Filter (Checkboxes at the top of the main section) ---
st.subheader("Filter by Benefit Topics")
selected_topics = []
cols = st.columns(len(BENEFIT_TOPICS))
for i, topic in enumerate(BENEFIT_TOPICS):
    if cols[i].checkbox(topic, value=False):
        selected_topics.append(topic)

df_benefit_filtered = filter_by_benefit_topics(df_companies_full, selected_topics)

# --- Pre-fetch Filtering UI (remains in sidebar) ---
st.sidebar.markdown('---')
st.sidebar.subheader('Pre-Fetch Company Filter')
company_count = len(df_benefit_filtered)
if company_count > 1:
    pre_min_rank, pre_max_rank = st.sidebar.slider(
        'Select rank range (pre-fetch)', 1, company_count, (1, min(50, company_count))
    )
    st.session_state['min_rank'] = pre_min_rank
    st.session_state['max_rank'] = pre_max_rank
else:
    pre_min_rank, pre_max_rank = 1, 1
    st.session_state['min_rank'] = pre_min_rank
    st.session_state['max_rank'] = pre_max_rank
    st.sidebar.info("Only one company available; rank range is fixed.")
pre_filter_options = st.sidebar.multiselect(
    'Pre-filter using:',
    ['Composite Score', 'Revenue', 'Profit'],
    default=['Composite Score'],
    key='pre_filter_options_multiselect'
)
pre_company_options = (df_benefit_filtered['종목코드'] + ' - ' + df_benefit_filtered.get('회사명', df_benefit_filtered['종목코드'])).drop_duplicates() if '회사명' in df_benefit_filtered.columns else df_benefit_filtered['종목코드'].drop_duplicates()
pre_selected_companies = st.sidebar.multiselect(
    'Pre-select specific companies (optional)',
    options=pre_company_options,
    default=[],
    key='pre_selected_companies_multiselect'
)
st.sidebar.markdown('---')

# Use df_benefit_filtered for pre-filtering and ranking
pre_filtered = df_benefit_filtered.copy()
# Dynamically find the latest 매출액 column for Revenue sorting
revenue_year_cols = [col for col in pre_filtered.columns if '매출액' in col and '원' in col and col[:4].isdigit()]
latest_revenue_col = sorted(revenue_year_cols, reverse=True)[0] if revenue_year_cols else None

if 'Revenue' in pre_filter_options and latest_revenue_col:
    pre_filtered = pre_filtered.sort_values(latest_revenue_col, ascending=False)
if 'Profit' in pre_filter_options and latest_revenue_col:
    pass  # Placeholder for future profit column
if 'Composite Score' in pre_filter_options:
    pass  # Already sorted by composite score if available
pre_filtered = pre_filtered.iloc[pre_min_rank-1:pre_max_rank].copy()
if pre_selected_companies:
    pre_filtered = pre_filtered[pre_company_options.isin(pre_selected_companies)]

# Before any access to '매출액', add a check and debug print
# st.write('DEBUG: pre_filtered columns before 매출액 access:', pre_filtered.columns.tolist())
if '매출액' in pre_filtered.columns:
    pre_filtered = pre_filtered.sort_values('매출액', ascending=False)
else:
    st.warning("'매출액' column not found in pre_filtered DataFrame. Columns are: " + str(pre_filtered.columns.tolist()))

# Before the fetch loop in the Fetch and Rank Selected Companies button handler
# st.write('DEBUG: pre_filtered shape before fetch:', pre_filtered.shape)
# st.write('DEBUG: pre_filtered company names:', pre_filtered['회사명'].tolist())

# Add this in your sidebar, before the fetch button
current_year = datetime.datetime.now().year
selected_year = st.sidebar.number_input(
    "Select year for financial data",
    min_value=2015,
    max_value=current_year,
    value=current_year,
    step=1
)
selected_years = [selected_year - 1, selected_year]  # [previous, current]

# Button to fetch and rank only selected companies
if st.sidebar.button('Fetch and Rank Selected Companies'):
    with st.spinner('Fetching and ranking selected companies. This may take a few minutes...'):
        records = []
        debug_fetch_log = []  # Collect debug info
        for idx, row in pre_filtered.iterrows():
            stock_code = row['종목코드']
            corp_code = corp_map.get(stock_code)
            fallback_revenue = row['매출액'] if '매출액' in row else 0
            fallback_profit = row['당기순이익'] if '당기순이익' in row else 0
            if not corp_code:
                debug_fetch_log.append(f"Skipping {row['회사명']} ({stock_code}): No corp_code found. Using CSV revenue: {fallback_revenue}")
                fin = {"매출액": fallback_revenue, "당기순이익": fallback_profit}
            else:
                try:
                    fin = fetch_financials(corp_code, year=str(selected_years[1]))
                    # Fetch previous year for YoY growth
                    try:
                        fin_prev = fetch_financials(corp_code, year=str(selected_years[0]))
                    except Exception:
                        fin_prev = {"매출액": 0, "당기순이익": 0}
                    # If API returns 0, fallback to CSV
                    if not fin.get('매출액'):
                        fin['매출액'] = fallback_revenue
                        debug_fetch_log.append(f"API revenue missing for {row['회사명']} ({stock_code}), using CSV revenue: {fallback_revenue}")
                    if not fin.get('당기순이익'):
                        fin['당기순이익'] = fallback_profit
                        debug_fetch_log.append(f"API profit missing for {row['회사명']} ({stock_code}), using CSV profit: {fallback_profit}")
                    fin['종목코드'] = stock_code
                    fin['회사명'] = row['회사명'] if '회사명' in row else stock_code
                    # YoY growth for revenue
                    prev_revenue = fin_prev.get('매출액', 0)
                    fin['매출액 YoY'] = (fin['매출액'] - prev_revenue) / abs(prev_revenue) if prev_revenue else 0
                    # YoY growth for profit
                    prev_profit = fin_prev.get('당기순이익', 0)
                    fin['당기순이익 YoY'] = (fin['당기순이익'] - prev_profit) / abs(prev_profit) if prev_profit else 0
                    debug_fetch_log.append(f"Fetched: {row['회사명']} ({stock_code}) - 주요값: 매출액={fin.get('매출액')}, 당기순이익={fin.get('당기순이익')}, 매출액 YoY={fin['매출액 YoY']:.2%}, 당기순이익 YoY={fin['당기순이익 YoY']:.2%}")
                except Exception as e:
                    debug_fetch_log.append(f"Error fetching {row['회사명']} ({stock_code}): {e}. Using CSV revenue: {fallback_revenue}")
                    fin = {"매출액": fallback_revenue, "당기순이익": fallback_profit, '종목코드': stock_code, '회사명': row['회사명'] if '회사명' in row else stock_code, '매출액 YoY': 0, '당기순이익 YoY': 0}
            records.append(fin)
        # Always show debug log after fetching
        st.info('Fetch debug log:')
        st.code('\n'.join(debug_fetch_log))
        if not records:
            st.warning('No valid company data was fetched. See debug log above.')
            st.stop()
    df = pd.DataFrame(records)
    # Ensure all required columns exist, fill missing with 0
    required_cols = [
        "당기순이익", "매출액", "법인세차감전 순이익", "부채총계", "영업비용", "영업이익",
        "유동부채", "유동자산", "이익잉여금", "자본금", "자본총계", "자산총계", "총포괄손익",
        "매출액 YoY", "당기순이익 YoY"
    ]
    for col in required_cols:
        if col not in df.columns:
            df[col] = 0
    # Convert all relevant columns to numeric, coercing errors to NaN and filling with 0
    for col in ["매출액", "영업이익", "당기순이익", "법인세차감전 순이익", "영업비용", "부채총계", "유동부채", "유동자산", "이익잉여금", "자본금", "자본총계", "자산총계", "총포괄손익"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    # Calculate financial ratios
    if '매출액' in df.columns and '영업이익' in df.columns:
        df['영업이익률'] = df['영업이익'] / df['매출액']
    else:
        st.warning("'매출액' or '영업이익' column not found in DataFrame. Columns are: " + str(df.columns.tolist()))
    df['순이익률'] = df['당기순이익'] / df['매출액']
    df['세전이익률'] = df['법인세차감전 순이익'] / df['매출액']
    df['영업비용률'] = df['영업비용'] / df['매출액']
    df['부채비율'] = df['부채총계'] / df['자산총계']
    df['D/E'] = df['부채총계'] / df['자본총계']
    df['유동비율'] = df['유동자산'] / df['유동부채']
    df['자기자본비율'] = df['자본총계'] / df['자산총계']
    df['재무레버리지'] = df['자산총계'] / df['자본총계']
    df['총포괄손익률'] = df['총포괄손익'] / df['매출액']
    df['이익잉여금비율'] = df['이익잉여금'] / df['자본총계']
    df['자산배율'] = df['자산총계'] / df['자본금']
    # Ranking
    better_high = [
        'ROA','ROE','영업이익률','순이익률','세전이익률',
        '유동비율','자기자본비율','총포괄손익률','이익잉여금비율',
        '매출액 YoY','당기순이익 YoY'
    ]
    better_low = [
        '영업비용률','부채비율','D/E','재무레버리지','자산배율'
    ]
    for col in better_high:
        if col in df.columns:
            df[f'{col}_rank'] = df[col].rank(ascending=False, method='min')
        else:
            st.info(f"Column '{col}' not found. Ranking for {col} will be set to 0.")
            df[f'{col}_rank'] = 0
    for col in better_low:
        if col in df.columns:
            df[f'{col}_rank'] = df[col].rank(ascending=True, method='min')
        else:
            st.info(f"Column '{col}' not found. Ranking for {col} will be set to 0.")
            df[f'{col}_rank'] = 0
    rank_cols = [c for c in df.columns if c.endswith('_rank')]
    df['CompositeScore'] = df[rank_cols].mean(axis=1)
    top500 = df.sort_values('CompositeScore').head(500).reset_index(drop=True)
    if top500.empty or '종목코드' not in top500.columns:
        st.error('No valid company data was fetched. Please adjust your filters or try again later.')
        st.stop()
    st.session_state['top500'] = top500
    st.session_state['rank_cols'] = rank_cols
    st.session_state['company_options'] = pre_company_options
    st.session_state['selected_companies'] = pre_selected_companies
    st.session_state['filter_options'] = pre_filter_options
    st.session_state['growth_option'] = 'None'

    # Only apply further filtering if user selected specific companies
    if pre_selected_companies:
        filtered = top500[top500['종목코드'].isin([c.split(' - ')[0] for c in pre_selected_companies])]
    else:
        filtered = top500.copy()

    # If user wants a specific rank range, apply it here
    filtered = filtered.iloc[pre_min_rank-1:pre_max_rank].copy()

    # Sort by the selected metric
    if 'Revenue' in pre_filter_options and '매출액' in filtered.columns:
        filtered = filtered.sort_values('매출액', ascending=False)
    if 'Profit' in pre_filter_options and '당기순이익' in filtered.columns:
        filtered = filtered.sort_values('당기순이익', ascending=False)
    if 'Composite Score' in pre_filter_options:
        filtered = filtered.sort_values('CompositeScore')

    st.session_state['filtered'] = filtered
    st.session_state['filtered_ready'] = True

# Show table and chart if available in session state
if st.session_state.get('filtered_ready') and 'filtered' in st.session_state:
    filtered = st.session_state['filtered']
    rank_cols = st.session_state['rank_cols']
    min_rank = st.session_state['min_rank']
    max_rank = st.session_state['max_rank']
    selected_companies = st.session_state['selected_companies']
    filter_options = st.session_state['filter_options']
    growth_option = st.session_state['growth_option']
    top500 = st.session_state['top500']
    # Before any access to '매출액', add a check and debug print
    # st.write('DEBUG: st.session_state["filtered"] columns before 매출액 access:', st.session_state['filtered'].columns.tolist())
    if '매출액' in st.session_state['filtered'].columns:
        st.session_state['filtered'] = st.session_state['filtered'].sort_values('매출액', ascending=False)
    else:
        st.warning("'매출액' column not found in filtered DataFrame. Columns are: " + str(st.session_state['filtered'].columns.tolist()))
    # Dynamically set the title based on the number of filtered companies and filter type
    filtered_count = len(filtered)
    if selected_companies:
        filter_desc = "by Company Selection"
    elif 'Revenue' in filter_options:
        filter_desc = "by Revenue"
    elif 'Profit' in filter_options:
        filter_desc = "by Profit"
    elif 'Composite Score' in filter_options:
        filter_desc = "by Composite Score"
    else:
        filter_desc = ""
    if filtered_count < len(top500):
        range_desc = f" (Rank {min_rank}-{max_rank})"
    else:
        range_desc = ""
    st.subheader(f'Filtered Top {filtered_count} Selection {filter_desc}{range_desc}')
    # Build company_tooltips dictionary from available info columns
    company_tooltips = {}
    if 'Gemini_Info' in filtered.columns:
        company_tooltips = dict(zip(filtered['회사명'], filtered['Gemini_Info'].fillna('')))
    elif 'OpenAI_Info' in filtered.columns:
        company_tooltips = dict(zip(filtered['회사명'], filtered['OpenAI_Info'].fillna('')))
    else:
        company_tooltips = dict(zip(filtered['회사명'], [''] * len(filtered)))
    # Build tooltip with company description and key metrics
    def build_tooltip(row):
        desc = company_tooltips.get(row['회사명'], '').replace('**', '')
        metrics = []
        if '매출액' in row and pd.notnull(row['매출액']):
            metrics.append(f"매출액: {row['매출액']}")
        if '당기순이익' in row and pd.notnull(row['당기순이익']):
            metrics.append(f"당기순이익: {row['당기순이익']}")
        if 'CompositeScore' in row and pd.notnull(row['CompositeScore']):
            metrics.append(f"CompositeScore: {row['CompositeScore']:.2f}")
        metrics_str = '\n'.join(metrics)
        return f"{desc}\n{metrics_str}" if metrics_str else desc
    # Define the base columns to show
    show_cols_final = ['회사명', '매출액', '당기순이익', '영업이익', '영업이익률', '순이익률', '세전이익률', '영업비용률', '부채비율', 'D/E', '유동비율', '자기자본비율', '재무레버리지', '총포괄손익률', '이익잉여금비율', '자산배율']
    # Always include these extra columns if they exist, right after 회사명
    preferred_extra_cols = ['OpenAI_Info', 'OpenAI_Hashtags', '업종', '주요제품']
    insert_at = 1  # after 회사명
    extra_cols = [col for col in preferred_extra_cols if col in filtered.columns]
    # Add any other extra columns (e.g., Gemini_Info) that are not already included
    for col in ['회사설명', '회사소개', 'Gemini_Info']:
        if col in filtered.columns and col not in show_cols_final and col not in extra_cols:
            extra_cols.append(col)
    show_cols_final_extended = show_cols_final.copy()
    for i, col in enumerate(extra_cols):
        show_cols_final_extended.insert(insert_at + i, col)
    table_data = (
        filtered[show_cols_final_extended]
        .copy()
        .drop_duplicates(subset=['회사명'], keep='first')
        .reset_index(drop=True)
    )
    table_data['회사소개(툴팁)'] = table_data.apply(build_tooltip, axis=1)
    gb = GridOptionsBuilder.from_dataframe(table_data)
    gb.configure_column('회사명', header_name='회사명', tooltipField='회사소개(툴팁)', autoHeight=True, wrapText=True, width=220)
    for col in show_cols_final_extended:
        if col != '회사명':
            gb.configure_column(col, wrapText=True, autoHeight=True, width=160)
    grid_options = gb.build()
    AgGrid(
        table_data,
        gridOptions=grid_options,
        enable_enterprise_modules=False,
        allow_unsafe_jscode=True,
        height=500,
        theme='streamlit',
    )
    # Download button
    import io
    excel_buffer = io.BytesIO()
    filtered.to_excel(excel_buffer, index=False, engine='openpyxl')
    excel_buffer.seek(0)
    st.download_button(
        label='Download Selection as Excel',
        data=excel_buffer,
        file_name='filtered_top500_composite_stocks.xlsx',
        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

# Move this section to the bottom
st.subheader('Other Types of Information (account_nm) from DART API')
account_nm_set = set()
if account_nm_set:
    st.write(sorted(account_nm_set))
else:
    st.info('No account_nm information found for the selected companies and years.')

# --- Market Sentiment Indicators (Main Section) ---
st.subheader('Market Sentiment')
vkospi, vkospi_debug = get_vkospi()
if vkospi is not None:
    st.metric('VKOSPI (Korean VIX)', f"{vkospi:.2f}")
else:
    st.info('VKOSPI data not available.')
    st.caption(f"Debug: {vkospi_debug}")

us_vix, us_vix_debug = get_us_vix()
if us_vix is not None:
    st.metric('US VIX (S&P 500)', f"{us_vix:.2f}")
else:
    st.info('US VIX data not available.')
    st.caption(f"Debug: {us_vix_debug}")

# MacroMicro Fear & Greed reference only
st.info('Check the latest Fear & Greed Index at MacroMicro:')
st.markdown('[View MacroMicro Fear & Greed Chart](https://en.macromicro.me/charts/50108/cnn-fear-and-greed)')
