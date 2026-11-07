import time

from sqlalchemy import text
from sqlalchemy.orm import Session


def check_database(db: Session) -> float:
    started = time.perf_counter()
    db.execute(text("SELECT 1"))
    return (time.perf_counter() - started) * 1000
