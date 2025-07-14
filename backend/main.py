import glob
from datetime import datetime
import os
import time
from pathlib import Path
import subprocess
import json
import logging
from urllib.parse import quote

import httpx
from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse, RedirectResponse
from typing import Optional

from database import save_search, get_history

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Определяем корневую директорию проекта
PROJECT_ROOT = Path(__file__).parent.parent  # Поднимаемся на два уровня вверх от backend/

# Путь к директории с данными
SCRAPY_DATA_DIR = PROJECT_ROOT / "scrapy_data"
SCRAPY_DATA_DIR.mkdir(exist_ok=True)  # Создаем директорию, если ее нет

def get_scrapy_data_path(filename: str) -> str:
    """Возвращает полный путь к файлу в директории scrapy_data"""
    return str(SCRAPY_DATA_DIR / filename)

def get_scrapy_full_path(filename: str, subdir: str = "") -> str:
    """Возвращает полный путь к файлу в директории scrapy_data"""
    path = SCRAPY_DATA_DIR
    if subdir:
        path = path / subdir
        path.mkdir(exist_ok=True)  # Создаем поддиректорию, если ее нет
    return str(path / filename)

@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})



@app.post("/search")
async def search(
    request: Request,
    query: str = Form(...),
    category: Optional[str] = Form(None),
    pages: int = Form(1),
    limit: int = Form(10),
    min_price: Optional[str] = Form(None),
    max_price: Optional[str] = Form(None)
):
    try:
        # Преобразование и валидация цен
        min_price_float = float(min_price) if min_price and min_price.strip() else None
        max_price_float = float(max_price) if max_price and max_price.strip() else None

        if min_price_float is not None and min_price_float < 0:
            return RedirectResponse(url="/?error=min_price_negative", status_code=303)
        if max_price_float is not None and max_price_float < 0:
            return RedirectResponse(url="/?error=max_price_negative", status_code=303)
        if min_price_float is not None and max_price_float is not None and min_price_float > max_price_float:
            return RedirectResponse(url="/?error=invalid_price_range", status_code=303)

        # Логирование параметров
        logger.info(
            f"Starting search with params: query={query}, category={category}, pages={pages}, limit={limit}, min_price={min_price_float}, max_price={max_price_float}")

        # Формирование имени файла
        safe_query = "".join(c if c.isalnum() else "_" for c in query)
        output_file = str(SCRAPY_DATA_DIR / f"{safe_query}_{int(time.time())}.json")

        # Формирование команды Scrapy
        cmd = ["scrapy", "crawl", "wildberries_v2"]

        # Добавляем параметры только если они не None
        params = {
            "queries": query,
            "pages": str(pages),
            "limit": str(limit),
        }

        if category:
            params["categories"] = category
        if min_price_float is not None:
            params["min_price"] = str(min_price_float)
        if max_price_float is not None:
            params["max_price"] = str(max_price_float)

        for key, value in params.items():
            cmd.extend(["-a", f"{key}={value}"])

        cmd.extend(["-o", output_file])

        logger.info(f"Running command: {' '.join(cmd)}")

        # Запуск Scrapy
        process = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300
        )

        # Обработка результатов
        if process.returncode != 0:
            logger.error(f"Scrapy process failed: {process.stderr}")
            return RedirectResponse(url="/?error=scrapy_failed", status_code=303)

        if not os.path.exists(output_file):
            logger.warning(f"Output file not found: {output_file}")
            return RedirectResponse(url="/?error=no_results", status_code=303)

        with open(output_file, "r", encoding="utf-8") as f:
            results = json.load(f)

        if not results:
            logger.warning(f"No results found in file: {output_file}")
            return RedirectResponse(url="/?error=no_products", status_code=303)

        # Сохранение в историю
        save_search(
            query=query,
            category=category,
            pages=pages,
            limit=limit,
            min_price=min_price_float,
            max_price=max_price_float
        )

        return templates.TemplateResponse(
            "results.html",
            {
                "request": request,
                "query": query,
                "category": category or "Все категории",
                "products": results[:limit],
                "now": datetime.now,
                "price_range": f"{min_price_float or 0} - {max_price_float or '∞'} руб"
            }
        )

    except subprocess.TimeoutExpired:
        logger.error("Scrapy process timed out")
        return RedirectResponse(url="/?error=timeout", status_code=303)
    except json.JSONDecodeError:
        logger.error("Failed to parse scrapy output")
        return RedirectResponse(url="/?error=parse_error", status_code=303)
    except Exception as e:
        logger.error(f"Search error: {str(e)}", exc_info=True)
        return RedirectResponse(url="/?error=unexpected", status_code=303)


@app.get("/history")
async def history(request: Request):
    try:
        searches = get_history()
        return templates.TemplateResponse(
            "history.html",
            {
                "request": request,
                "searches": searches,
                "format_price": lambda p: f"{p/100:.2f} руб" if p is not None else "Не указано",
                "format_date": lambda d: d.strftime("%d.%m.%Y %H:%M") if d is not None else ""
            }
        )
    except Exception as e:
        logger.error(f"Failed to get history: {str(e)}", exc_info=True)
        return RedirectResponse(url="/?error=history_error", status_code=303)


from fastapi import BackgroundTasks
import asyncio


async def _fetch_product_photos(product_id: int):
    """Запуск паука для получения фотографий товара"""
    photos_dir = "photos"
    output_file = get_scrapy_full_path(f"photos_{product_id}.json", photos_dir)

    try:
        # Создаем директорию photos, если ее нет
        (SCRAPY_DATA_DIR / photos_dir).mkdir(exist_ok=True)

        # Удаляем старый файл, если он существует
        if os.path.exists(output_file):
            os.remove(output_file)

        process = subprocess.run(
            [
                "scrapy", "crawl", "wb_product_photos",
                "-a", f"product_id={product_id}",
                "-O", output_file,  # Используем -O для перезаписи
                "--loglevel", "ERROR"
            ],
            cwd=str(PROJECT_ROOT),
            timeout=120,
            capture_output=True,
            text=True
        )

        if process.returncode == 0 and os.path.exists(output_file):
            with open(output_file, "r", encoding="utf-8") as f:
                content = f.read().strip()
                # Очищаем JSON
                last_valid_bracket = content.rfind(']')
                if last_valid_bracket > 0:
                    content = content[:last_valid_bracket + 1]

                lines = [line for line in content.split('\n')
                         if '"timestamp"' not in line and line.strip()]
                cleaned_content = '\n'.join(lines)

                try:
                    data = json.loads(cleaned_content)
                    if isinstance(data, list):
                        # Удаляем дубликаты
                        unique_photos = []
                        seen_urls = set()
                        for photo in data:
                            if isinstance(photo, dict) and 'image_url' in photo:
                                if photo['image_url'] not in seen_urls:
                                    seen_urls.add(photo['image_url'])
                                    unique_photos.append(photo)
                        return unique_photos
                except json.JSONDecodeError:
                    logger.error("Failed to parse photos JSON")
    except Exception as e:
        logger.error(f"Photos spider failed: {str(e)}")
    return []


@app.get("/product/{product_id}")
async def product_details(request: Request, product_id: int, background_tasks: BackgroundTasks):
    try:
        # 1. Get base data
        base_data = find_product_in_data(product_id) or {}
        base_data['product_id'] = product_id
        base_data['url'] = f"https://www.wildberries.ru/catalog/{product_id}/detail.aspx"

        # 2. Try to get details via direct API
        api_data = await _fetch_direct_api(product_id)
        if api_data:
            base_data.update(api_data)

        # 3. If no characteristics found, run Scrapy spider in background
        if not base_data.get('options') and not base_data.get('grouped_options'):
            background_tasks.add_task(_fetch_via_scrapy, product_id)

        # 4. Start photos parsing in background
        background_tasks.add_task(_fetch_product_photos, product_id)

        # 5. Check if there are already saved photos
        photos_dir = "photos"
        photos_file = get_scrapy_full_path(f"photos_{product_id}.json", photos_dir)
        if os.path.exists(photos_file):
            with open(photos_file, "r", encoding="utf-8") as f:
                base_data['photos'] = json.load(f)

        # 6. Add cookie data if exists
        if cookie_data := request.cookies.get(f"product_{product_id}"):
            try:
                base_data.update(json.loads(cookie_data))
            except json.JSONDecodeError:
                pass

        return _render_product_response(request, base_data)

    except Exception as e:
        logger.error(f"Product details error: {str(e)}")
        error_data = {
            'product_id': product_id,
            'error': 'Произошла ошибка при получении данных',
            'url': f"https://www.wildberries.ru/catalog/{product_id}/detail.aspx"
        }
        return _render_product_response(request, error_data)


def _render_product_response(request: Request, product_data: dict):
    """Рендеринг страницы с деталями товара"""
    # Обязательные поля
    product_data.setdefault('product_id', 'N/A')
    product_data.setdefault('name', f"Товар #{product_data['product_id']}")

    # Добавляем URL товара на WB, если не указан
    if 'url' not in product_data:
        product_data['url'] = f"https://www.wildberries.ru/catalog/{product_data['product_id']}/detail.aspx"

    # Добавляем базовые данные из cookies
    if cookie_data := request.cookies.get(f"product_{product_data['product_id']}"):
        try:
            product_data.update(json.loads(cookie_data))
        except json.JSONDecodeError:
            pass

    return templates.TemplateResponse(
        "product_details.html",
        {
            "request": request,
            "product": product_data,
            "now": datetime.now
        }
    )


async def _fetch_direct_api(product_id: int):
    """Прямой запрос к API Wildberries с обработкой 404"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            for basket_num in range(1, 41):
                url = f"https://basket-{basket_num:02d}.wbbasket.ru/vol{str(product_id)[:4]}/part{str(product_id)[:6]}/{product_id}/info/ru/card.json"
                try:
                    response = await client.get(url)
                    if response.status_code == 200:
                        data = response.json()
                        data['product_id'] = product_id
                        return data
                except httpx.HTTPStatusError as e:
                    if e.response.status_code != 404:
                        logger.warning(f"API error for {product_id}: {str(e)}")
                    continue
                except Exception as e:
                    logger.warning(f"Request failed for {product_id}: {str(e)}")
                    continue
    except Exception as e:
        logger.error(f"Direct API fetch error: {str(e)}")
    return None


async def _fetch_via_scrapy(product_id: int):
    """Запуск Scrapy паука с обработкой ошибок"""
    output_file = get_scrapy_data_path(f"product_{product_id}_{int(time.time())}.json")

    try:
        process = subprocess.run(
            [
                "scrapy", "crawl", "wb_product_details",
                "-a", f"product_ids={product_id}",
                "-o", output_file,
                "--loglevel", "ERROR"  # Уменьшаем объем логов
            ],
            cwd=str(PROJECT_ROOT),
            timeout=120,
            capture_output=True,
            text=True
        )

        if process.returncode == 0 and os.path.exists(output_file):
            with open(output_file, "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                    return data[0] if data else None
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON in {output_file}")
                    return None
    except subprocess.TimeoutExpired:
        logger.error("Scrapy process timed out")
    except Exception as e:
        logger.error(f"Scrapy process failed: {str(e)}")

    return None


def find_product_in_data(product_id: int):
    """Ищем товар в data.json по ID"""
    data_file = Path(__file__).parent.parent / "scrapy_data" / "data.json"

    if not data_file.exists():
        return None

    try:
        with open(data_file, 'r', encoding='utf-8') as f:
            products = json.load(f)
            for product in products:
                if product.get('product_id') == product_id:
                    return {
                        'price': product.get('price'),
                        'rating': product.get('rating'),
                        'reviews_count': product.get('reviews_count')
                    }
    except Exception as e:
        logger.error(f"Error reading data.json: {str(e)}")

    return None


@app.get("/api/product_photos/{product_id}")
async def get_product_photos(product_id: int):
    photos_file = get_scrapy_data_path(f"photos_{product_id}.json")

    if not os.path.exists(photos_file):
        return JSONResponse({"photos": []}, status_code=404)

    try:
        with open(photos_file, "r", encoding="utf-8") as f:
            content = f.read().strip()

            # Обрабатываем разные форматы JSON
            if content.startswith('[') and content.endswith(']'):
                # Это массив объектов
                return {"photos": json.loads(content)}
            elif content.startswith('{') and content.endswith('}'):
                # Это один объект
                data = json.loads(content)
                return {"photos": [data] if isinstance(data, dict) else data}
            else:
                # Это несколько JSON объектов (по одному на строку)
                photos = []
                for line in content.split('\n'):
                    if line.strip():
                        photos.append(json.loads(line))
                return {"photos": photos}

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON file {photos_file}: {str(e)}")
        return JSONResponse(
            {"error": "Invalid photo data format", "details": str(e)},
            status_code=500
        )
    except Exception as e:
        logger.error(f"Error reading photo file: {str(e)}")
        return JSONResponse(
            {"error": "Failed to read photo data", "details": str(e)},
            status_code=500
        )


@app.get("/product/{product_id}/photos")
async def get_product_photos(product_id: int):
    """Получает фотографии товара, запуская паука при необходимости"""
    photos_dir = "photos"
    photos_file = f"photos_{product_id}.json"
    photos_path = get_scrapy_full_path(photos_file, photos_dir)

    # Если файл не существует или старше 5 минут - запускаем паука
    if not os.path.exists(photos_path) or (time.time() - os.path.getmtime(photos_path)) > 300:
        try:
            # Создаем директорию photos, если ее нет
            (SCRAPY_DATA_DIR / photos_dir).mkdir(exist_ok=True)

            # Удаляем старый файл, если он существует
            if os.path.exists(photos_path):
                os.remove(photos_path)

            process = subprocess.run(
                [
                    "scrapy", "crawl", "wb_product_photos",
                    "-a", f"product_id={product_id}",
                    "-O", photos_path,  # Используем -O вместо -o для перезаписи файла
                    "--loglevel", "ERROR"
                ],
                cwd=str(PROJECT_ROOT),
                timeout=120,
                capture_output=True,
                text=True
            )

            if process.returncode != 0:
                logger.error(f"Scrapy failed: {process.stderr}")
                return {"photos": [], "error": "Failed to fetch photos"}
        except Exception as e:
            logger.error(f"Error running spider: {str(e)}")
            return {"photos": [], "error": str(e)}

    # Читаем и валидируем JSON
    if os.path.exists(photos_path):
        try:
            with open(photos_path, "r", encoding="utf-8") as f:
                content = f.read().strip()

                # Удаляем все после последнего корректного закрытия массива
                last_valid_bracket = content.rfind(']')
                if last_valid_bracket > 0:
                    content = content[:last_valid_bracket + 1]

                # Удаляем все строки с timestamp
                lines = [line for line in content.split('\n')
                         if '"timestamp"' not in line and line.strip()]
                cleaned_content = '\n'.join(lines)

                try:
                    data = json.loads(cleaned_content)
                    if isinstance(data, list):
                        # Удаляем дубликаты по image_url
                        unique_photos = []
                        seen_urls = set()
                        for photo in data:
                            if isinstance(photo, dict) and 'image_url' in photo:
                                if photo['image_url'] not in seen_urls:
                                    seen_urls.add(photo['image_url'])
                                    unique_photos.append(photo)
                        return {"photos": unique_photos}
                    return {"photos": []}
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON in photo file: {str(e)}")
                    return {"photos": [], "error": "Invalid photo data format"}
        except Exception as e:
            logger.error(f"Error reading photos file: {str(e)}")
            return {"photos": [], "error": str(e)}

    return {"photos": [], "status": "not_found"}


@app.get("/api/product/{product_id}")
async def get_product_data(product_id: int):
    """Check for product data including characteristics"""
    # 1. Check direct API first
    api_data = await _fetch_direct_api(product_id)
    if api_data:
        return api_data

    # 2. Check if there's a recently saved file
    product_file = get_scrapy_data_path(f"product_{product_id}_*.json")
    recent_files = sorted(glob.glob(product_file), key=os.path.getmtime, reverse=True)

    if recent_files:
        try:
            with open(recent_files[0], "r", encoding="utf-8") as f:
                data = json.load(f)
                return data[0] if isinstance(data, list) else data
        except Exception as e:
            logger.error(f"Error reading product file: {str(e)}")

    return {"status": "not_found"}


@app.post("/analyze-product")
async def analyze_product(data: dict):
    try:
        PROMPT_TEMPLATE = """
        Проанализируй товар для интернет-магазина Wildberries. 
        Ты - опытный продавец-консультант, который помогает покупателям сделать выбор.
        Ответ должен быть менее 300 символов! Нельзя называть артикул товара (Товар #367782204 - ТАК НЕЛЬЗЯ)

        Вот данные о товаре:
        Название: {name}
        Бренд: {brand}
        Описание: {description}
        Цена: {price} ₽
        Рейтинг: {rating} (отзывов: {reviews_count})
        Артикул: {vendor_code} НЕЛЬЗЯ О НЕМ УПОМИНАТЬ В ОТВЕТЕ

        Характеристики:
        {specs}

        Сделай анализ по следующей структуре:
        1. Краткое описание товара (1 предложение) короткое
        2. Основные преимущества (1 пункт)
        3. На что обратить внимание (1 потенциальных недостатка или особенности)
        4. Общий вывод и соотношение цена качество

        Будь кратким, но информативным. Пиши на русском языке. 
        Используй маркированные списки для удобства чтения.
        Ответ должен быть менее 300 символов! Нельзя называть артикул товара (Товар #367782204 - ТАК НЕЛЬЗЯ)
        """
        # 1. Безопасное формирование спецификаций
        specs = []
        for opt in data.get('options', []):
            try:
                group = str(opt.get('group', '')).strip()
                name = str(opt.get('name', '')).strip()
                value = str(opt.get('value', '')).strip()
                if name and value:
                    specs.append(f"- {group} {name}: {value}")
            except Exception as e:
                logger.warning(f"Ошибка обработки характеристики: {opt} - {str(e)}")

        specs_str = "\n".join(specs) if specs else "Нет характеристик"

        # 2. Безопасное форматирование цены
        try:
            price = int(float(data.get('price', 0)))
            price_str = f"{price} ₽"
        except:
            price_str = "Нет данных"

        # 3. Формирование промпта с защитой от ошибок
        prompt = PROMPT_TEMPLATE.format(
            name=str(data.get('name', 'Не указано')).replace('\n', ' ').strip(),
            brand=str(data.get('brand', 'Не указан')).replace('\n', ' ').strip(),
            description=str(data.get('description', 'Нет описания')).replace('\n', ' ').strip(),
            price=price_str,
            rating=str(data.get('rating', 'Нет рейтинга')),
            reviews_count=str(data.get('reviews_count', '0')),
            vendor_code=str(data.get('vendor_code', 'Нет артикула')),
            specs=specs_str
        )

        # 2. Запрос к Mistral с таймаутом
        async with httpx.AsyncClient() as client:
            logger.info("3/4: Отправка запроса к Mistral API...")
            response = await client.post(
                "https://api.mistral.ai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {'KhI0YjFOxFbXlPKeoVCxCqu1yhYYBxRz'}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "mistral-tiny",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.7,
                    "max_tokens": 1000
                },
                timeout=30.0  # Увеличенный таймаут
            )

            logger.info(f"4/4: Получен ответ {response.status_code}")

            if response.status_code != 200:
                error_msg = f"Mistral API error: {response.text}"
                logger.error(error_msg)
                raise HTTPException(status_code=502, detail=error_msg)

            result = response.json()
            if not result.get('choices'):
                logger.error(f"Неожиданный формат ответа: {result}")
                raise HTTPException(status_code=502, detail="Неверный формат ответа от Mistral")

            content = result['choices'][0]['message']['content'].strip()
            if not content:
                raise HTTPException(status_code=502, detail="Пустой ответ от Mistral")

            return {"analysis": content}

    except httpx.TimeoutException:
        logger.error("Таймаут при запросе к Mistral API")
        raise HTTPException(status_code=504, detail="Таймаут запроса к ИИ")
    except Exception as e:
        logger.error(f"Неожиданная ошибка: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))