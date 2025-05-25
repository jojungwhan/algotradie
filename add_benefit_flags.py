import pandas as pd
import openai
import time
from datetime import datetime

# Set your OpenAI API key directly
openai.api_key = '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'
MODEL_NAME = 'gpt-4o-mini'

BENEFIT_FLAGS = ['AI', 'Robotics', 'Defense', 'Environment', 'Bio', 'Longevity']

# Function to get flags from OpenAI
def get_benefit_flags(row):
    prompt = f"""
아래는 한국 상장기업의 정보입니다.
- 회사명: {row['회사명']}
- 업종: {row['업종']}
- 주요제품: {row['주요제품']}
- 회사 설명: {row.get('OpenAI_Info', '')}
- sector_tag_en: {row.get('sector_tag_en', '')}
- sector_tag_ko: {row.get('sector_tag_ko', '')}
- product_tags_en: {row.get('product_tags_en', '')}
- product_tags_ko: {row.get('product_tags_ko', '')}

각 분야에 해당하면 1, 아니면 0으로 답해주세요. 반드시 아래와 같은 JSON 형식으로만 답변하세요:
{{
  \"AI\": 0 또는 1,
  \"Robotics\": 0 또는 1,
  \"Defense\": 0 또는 1,
  \"Environment\": 0 또는 1,
  \"Bio\": 0 또는 1,
  \"Longevity\": 0 또는 1
}}
"""
    try:
        response = openai.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=256,
            temperature=0.0,
        )
        text = response.choices[0].message.content.strip()
        # Remove code block markers if present
        if text.startswith('```'):
            text = text.strip('`').strip()
            if text.lower().startswith('json'):
                text = text[4:].strip()
        import json
        try:
            flags = json.loads(text)
            return [int(flags.get(flag, 0)) for flag in BENEFIT_FLAGS]
        except Exception:
            print(f"[WARN] Could not parse JSON for {row['회사명']}: {text}")
            return [0]*len(BENEFIT_FLAGS)
    except Exception as e:
        print(f"[ERROR] OpenAI API error for {row['회사명']}: {e}")
        return [0]*len(BENEFIT_FLAGS)

def main():
    input_csv = 'korean_companies_with_openai_info_test_20250513_111511.csv'
    now_str = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_csv = f'korean_companies_with_benefit_flags_{now_str}.csv'
    df = pd.read_csv(input_csv, encoding='utf-8-sig')
    # Process all companies
    for flag in BENEFIT_FLAGS:
        df[flag] = 0
    for idx, row in df.iterrows():
        print(f"Processing {row['회사명']} ({idx+1}/{len(df)})...")
        flags = get_benefit_flags(row)
        for flag, val in zip(BENEFIT_FLAGS, flags):
            df.at[idx, flag] = val
        time.sleep(1)  # Be polite to the API
    df.to_csv(output_csv, index=False, encoding='utf-8-sig')
    print(f"Done. Saved to {output_csv}")

if __name__ == "__main__":
    main() 