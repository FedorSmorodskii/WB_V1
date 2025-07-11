from datetime import datetime
import os
import time
from pathlib import Path
import subprocess
import json
import logging
from urllib.parse import quote

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

# Создаем директорию для результатов, если ее нет
Path("scrapy_data").mkdir(exist_ok=True)


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
        output_file = f"scrapy_data/{safe_query}_{int(time.time())}.json"

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