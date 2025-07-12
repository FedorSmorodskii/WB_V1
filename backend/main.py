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


@app.get("/product/{product_id}")
async def product_details(request: Request, product_id: int):
    try:
        # 1. Ищем базовые данные в data.json
        base_data = find_product_in_data(product_id) or {}
        base_data['product_id'] = product_id
        base_data['url'] = f"https://www.wildberries.ru/catalog/{product_id}/detail.aspx"

        # 2. Пробуем получить детали через API
        api_data = await _fetch_direct_api(product_id)
        if api_data:
            base_data.update(api_data)

        # 3. Добавляем данные из cookies
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
