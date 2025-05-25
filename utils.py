# utils.py
import configparser
import os
from constants import INI_FILE

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