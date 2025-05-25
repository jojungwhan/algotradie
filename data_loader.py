# data_loader.py
import pandas as pd
from constants import BENEFIT_TOPICS
from utils import load_last_csv_path, save_last_csv_path
import streamlit as st
import os

def load_company_data(uploaded_file):
    df_companies = None
    if uploaded_file is not None:
        try:
            df_companies = pd.read_csv(uploaded_file, dtype={'종목코드': str}, encoding='utf-8-sig')
            if hasattr(uploaded_file, 'name') and not os.path.exists(uploaded_file.name):
                with open(uploaded_file.name, 'wb') as f:
                    f.write(uploaded_file.getbuffer())
            save_last_csv_path(uploaded_file.name)
            missing_cols = [col for col in BENEFIT_TOPICS if col not in df_companies.columns]
            if missing_cols:
                st.error(f"The uploaded CSV is missing required columns: {', '.join(missing_cols)}")
                st.stop()
            st.success("CSV file loaded successfully!")
            # After loading df_companies, create a unified '매출액' column if not present
            if '매출액' not in df_companies.columns:
                year_cols = [col for col in df_companies.columns if '매출액' in col]
                if year_cols:
                    year_cols_sorted = sorted(year_cols, reverse=True)
                    df_companies['매출액'] = df_companies[year_cols_sorted[0]]
                else:
                    st.warning("No '매출액' or year-specific 매출액 column found in uploaded CSV.")
        except Exception as e:
            st.error(f"Failed to parse the uploaded CSV file: {e}")
            st.stop()
    else:
        last_csv_path = load_last_csv_path()
        if last_csv_path and os.path.exists(last_csv_path):
            try:
                df_companies = pd.read_csv(last_csv_path, dtype={'종목코드': str}, encoding='utf-8-sig')
                st.info(f"Loaded last used CSV: {last_csv_path}")
                if '매출액' not in df_companies.columns:
                    year_cols = [col for col in df_companies.columns if '매출액' in col]
                    if year_cols:
                        year_cols_sorted = sorted(year_cols, reverse=True)
                        df_companies['매출액'] = df_companies[year_cols_sorted[0]]
                    else:
                        st.warning("No '매출액' or year-specific 매출액 column found in uploaded CSV.")
            except Exception as e:
                st.error(f"Failed to load last used CSV file: {e}")
                st.stop()
        else:
            st.info("Please upload a CSV file to proceed.")
            st.stop()
    return df_companies

def filter_by_benefit_topics(df, selected_topics):
    if selected_topics:
        missing_cols = [col for col in selected_topics if col not in df.columns]
        if missing_cols:
            st.warning(f"Selected topics not found in data: {', '.join(missing_cols)}. Please check your CSV or select different topics.")
            return df.copy()
        mask = (df[selected_topics] == 1).all(axis=1)
        return df[mask].copy()
    else:
        return df.copy() 