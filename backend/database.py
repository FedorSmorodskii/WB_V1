from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from typing import List, Dict, Any, Optional

Base = declarative_base()


class SearchHistory(Base):
    __tablename__ = 'search_history'

    id = Column(Integer, primary_key=True)
    query = Column(String(255), nullable=False)
    category = Column(String(100), nullable=True)
    pages = Column(Integer, nullable=False, default=1)
    items_count = Column(Integer, nullable=False, default=10)
    min_price = Column(Integer, nullable=True)
    max_price = Column(Integer, nullable=True)
    search_date = Column(DateTime, default=datetime.utcnow)


engine = create_engine('sqlite:///searches.db')
Base.metadata.create_all(engine)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Генератор сессий для работы с базой данных"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def save_search(
        query: str,
        category: Optional[str] = None,
        pages: int = 1,
        limit: int = 10,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None
):
    """Сохраняет историю поиска в базу данных"""
    with SessionLocal() as session:
        search = SearchHistory(
            query=query,
            category=category,
            pages=pages,
            items_count=limit,
            min_price=int(min_price * 100) if min_price is not None else None,
            max_price=int(max_price * 100) if max_price is not None else None
        )
        session.add(search)
        session.commit()


def get_history(limit: int = 100) -> List[Dict[str, Any]]:
    """Получает историю поисковых запросов в виде словарей"""
    with SessionLocal() as session:
        searches = session.query(SearchHistory) \
            .order_by(SearchHistory.search_date.desc()) \
            .limit(limit) \
            .all()

        # Преобразуем объекты в словари до закрытия сессии
        return [
            {
                "query": s.query,
                "category": s.category,
                "pages": s.pages,
                "items_count": s.items_count,
                "min_price": s.min_price,
                "max_price": s.max_price,
                "search_date": s.search_date
            }
            for s in searches
        ]