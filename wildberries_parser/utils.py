import json
from pathlib import Path
from typing import Dict, List, Union

def save_to_json(data: Union[Dict, List], filename: str):
    """Сохранение данных в JSON файл"""
    try:
        path = Path(filename)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"Error saving to JSON: {e}")
        return False

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