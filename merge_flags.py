import pandas as pd
import requests
import time
from datetime import datetime

GEMINI_API_KEY = 'AIzaSyDy6pR6fPkRkR8hrBYMP5ydo9TqJktmHUA'
GEMINI_API_URL = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=' + GEMINI_API_KEY

# Columns to update
BENEFIT_COLUMNS = [
    'Benefit_AI',
    'Benefit_Robotics',
    'Benefit_Defense',
    'Benefit_Environment',
    'Benefit_Bio',
    'Benefit_Longevity'
]

def get_benefit_flags(row):
    prompt = f"""
아래는 한국 상장기업의 정보입니다.
- 회사명: {row['회사명']}
- 업종: {row['업종']}
- 주요제품: {row['주요제품']}
- 회사 설명: {row.get('Gemini_Info', '')}
- sector_tag_en: {row.get('sector_tag_en', '')}
- sector_tag_ko: {row.get('sector_tag_ko', '')}
- product_tags_en: {row.get('product_tags_en', '')}
- product_tags_ko: {row.get('product_tags_ko', '')}

각 Benefit flag에 대해 해당 기업이 아래 분야에 해당하면 1, 아니면 0으로 답해주세요. 반드시 아래와 같은 JSON 형식으로만 답변하세요:
{{
  \"Benefit_AI\": 0 또는 1,
  \"Benefit_Defense\": 0 또는 1,
  \"Benefit_Environment\": 0 또는 1,
  \"Benefit_Bio\": 0 또는 1,
  \"Benefit_Longevity\": 0 또는 1,
  \"Benefit_Robotics\": 0 또는 1
}}
"""
    headers = {"Content-Type": "application/json"}
    data = {
        "contents": [
            {"parts": [{"text": prompt}]}
        ]
    }
    try:
        response = requests.post(GEMINI_API_URL, headers=headers, json=data)
        if response.status_code == 200:
            import json
            text = response.json()['candidates'][0]['content']['parts'][0]['text']
            # Remove code block markers if present
            if text.startswith('```'):
                text = text.strip('`').strip()
                # Remove 'json' if present after ```
                if text.lower().startswith('json'):
                    text = text[4:].strip()
            try:
                flags = json.loads(text)
                return [flags.get(col, row[col]) for col in BENEFIT_COLUMNS]
            except Exception:
                print(f"[WARN] Could not parse JSON for {row['회사명']}: {text}")
                return [row[col] for col in BENEFIT_COLUMNS]
        else:
            print(f"[ERROR] Gemini API error for {row['회사명']}: {response.status_code} {response.text}")
            return [row[col] for col in BENEFIT_COLUMNS]
    except Exception as e:
        print(f"[ERROR] Exception for {row['회사명']}: {e}")
        return [row[col] for col in BENEFIT_COLUMNS]

def main():
    input_csv = 'korean_companies_list_with_updated_flags.csv'
    now_str = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_csv = f'korean_companies_list_with_gemini_flags_{now_str}.csv'
    df = pd.read_csv(input_csv, encoding='utf-8-sig')
    df_sample = df.head(20).copy()
    # Ensure benefit columns are int type to avoid FutureWarning
    for col in BENEFIT_COLUMNS:
        if col in df_sample.columns:
            df_sample[col] = pd.to_numeric(df_sample[col], errors='coerce').fillna(0).astype(int)
    for idx, row in df_sample.iterrows():
        print(f"Processing {row['회사명']} ({idx+1}/20)...")
        new_flags = get_benefit_flags(row)
        for col, val in zip(BENEFIT_COLUMNS, new_flags):
            try:
                df_sample.at[idx, col] = int(val)
            except Exception:
                df_sample.at[idx, col] = val
        time.sleep(1)  # Be polite to the API
    df_sample.to_csv(output_csv, index=False, encoding='utf-8-sig')
    print(f"Done. Saved to {output_csv}")

if __name__ == "__main__":
    main()
