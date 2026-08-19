import psycopg2

from app.config import DATABASE_URL


def get_conn():
    return psycopg2.connect(DATABASE_URL)
