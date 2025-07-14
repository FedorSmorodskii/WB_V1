import json
from pathlib import Path
from typing import Dict, List, Union

def load_queries_from_file(filepath: str) -> List[str]:
    """Загрузка поисковых запросов из файла"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"File not found: {filepath}")
        return []
    except Exception as e:
        print(f"Error reading queries file: {e}")
        return []