from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

Base = declarative_base()

class SearchHistory(Base):
    __tablename__ = 'search_history'
    id = Column(Integer, primary_key=True)
    query = Column(String)
    category = Column(String)
    items_count = Column(Integer)
    search_date = Column(DateTime, default=datetime.now)

engine = create_engine('sqlite:///searches.db')
Base.metadata.create_all(engine)

Session = sessionmaker(bind=engine)

def save_search(query: str, category: str, count: int):
    session = Session()
    search = SearchHistory(query=query, category=category, items_count=count)
    session.add(search)
    session.commit()
    session.close()

def get_history():
    session = Session()
    history = session.query(SearchHistory).order_by(SearchHistory.search_date.desc()).all()
    session.close()
    return history