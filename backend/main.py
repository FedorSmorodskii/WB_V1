from datetime import datetime
import os
import time

from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
import subprocess
import json
from .database import save_search, get_history

app = FastAPI()
app.mount("/static", StaticFiles(directory="backend/static"), name="static")
templates = Jinja2Templates(directory="backend/templates")


@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


SCRAPY_CMD = "scrapy crawl wildberries_v2 -a queries={query} -a categories={category} -a limit={limit} -o {output}"


@app.post("/search")
async def search(
        request: Request,
        query: str = Form(...),
        category: str = Form(""),
        limit: int = Form(10)
):
    output_file = f"scrapy_data/{query.replace(' ', '_')}_{int(time.time())}.json"

    # Запускаем парсер
    cmd = SCRAPY_CMD.format(
        query=query,
        category=category,
        limit=limit,
        output=output_file
    )

    try:
        # Запускаем и ждем завершения
        process = subprocess.run(cmd, shell=True, check=True)

        # Проверяем существование файла
        if not os.path.exists(output_file):
            raise HTTPException(status_code=500, detail="Файл с результатами не был создан")

        # Читаем результаты
        with open(output_file, "r", encoding="utf-8") as f:
            results = json.load(f)

        # Сохраняем в историю
        save_search(query, category, limit)

        print("Пример товара:", results[0] if results else "Нет данных")

        return templates.TemplateResponse(
            "results.html",
            {
                "request": request,
                "query": query,
                "category": category or "Все категории",
                "products": results[:limit],
                "now": datetime.now

            }
        )

    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"Ошибка парсера: {str(e)}")
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Ошибка чтения результатов")


@app.get("/history")
async def history(request: Request):
    searches = get_history()
    return templates.TemplateResponse("history.html", {"request": request, "searches": searches})