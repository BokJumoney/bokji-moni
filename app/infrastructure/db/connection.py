# SQLAlchemy engine 및 SessionLocal 설정
import psycopg2
from pgvector.psycopg2 import register_vector


DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "edudb",
    "user": "edu",
    "password": "1234"
}


def get_connection():

    conn = psycopg2.connect(
        **DB_CONFIG
    )

    register_vector(conn)

    return conn