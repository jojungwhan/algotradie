import csv
import time
import re
import os
from datetime import datetime
import openai

# Set up OpenAI API key directly
openai.api_key = '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'

MODEL_NAME = 'gpt-4o-mini'

def get_company_info(company_name):
    prompt = f"'{company_name}' 회사에 대해 간단히 한국어로 소개해주고, 이 회사가 제공하는 제품과 서비스에 대해 해시태그(#) 형태로 출력해줘. 예시: #제품명 #서비스명"
    try:
        response = openai.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=512,
            temperature=0.7,
        )
        text = response.choices[0].message.content.strip()
        hashtags = extract_hashtags(text)
        return text, hashtags
    except Exception as e:
        print(f"OpenAI API error for {company_name}: {e}")
        return None, None

def extract_hashtags(text):
    # Extract hashtags (words starting with #, including Korean)
    return ' '.join(re.findall(r'#\w+', text))

def main():
    input_csv = 'korean_companies_full.csv'
    now_str = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_csv = f'korean_companies_with_openai_info_test_{now_str}.csv'
    with open(input_csv, newline='', encoding='utf-8') as csvfile, \
         open(output_csv, 'w', newline='', encoding='utf-8') as outfile:
        reader = csv.DictReader(csvfile)
        print('Detected CSV fieldnames:', reader.fieldnames)  # Debug print
        fieldnames = reader.fieldnames + ['OpenAI_Info', 'OpenAI_Hashtags']
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()
        for i, row in enumerate(reader):
            company_name = row['\ufeff회사명']  # Use the correct header with BOM
            print(f"Querying OpenAI for: {company_name}")
            info, hashtags = get_company_info(company_name)
            row['OpenAI_Info'] = info
            row['OpenAI_Hashtags'] = hashtags
            writer.writerow(row)
            time.sleep(1)  # Be polite to the API

if __name__ == "__main__":
    main()
