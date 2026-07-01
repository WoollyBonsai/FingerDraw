from sqlmodel import SQLModel, create_engine, Session
import os

DB_DIR = os.path.join(os.path.dirname(__file__), "db")
os.makedirs(DB_DIR, exist_ok=True)

sqlite_file_name = os.path.join(DB_DIR, "notebook.db")
sqlite_url = f"sqlite:///{sqlite_file_name}"

connect_args = {"check_same_thread": False}
engine = create_engine(sqlite_url, echo=False, connect_args=connect_args)

def create_db_and_tables():
    from .models import Note
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session
