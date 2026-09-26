from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import create_engine
from dotenv import load_dotenv
import os

load_dotenv()

DB_PASSWORD = os.getenv("POSTGRES_DB_PASSWORD")

# postgresql://[username]:[password]@[hostname]:[port]/[database_name]

DATABASE_URL = f"postgresql://postgres:{DB_PASSWORD}@localhost:5432/url_shortener"

engine = create_engine(
    DATABASE_URL, 
    # connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()