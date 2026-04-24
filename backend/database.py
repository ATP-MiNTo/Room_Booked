import psycopg2
import os

def get_db():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "db"),
        dbname=os.getenv("POSTGRES_DB", "complab"),
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD", "postgres"),
        port=os.getenv("POSTGRES_PORT", "5432")
    )

def init_sequences():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT setval('reservations_id_seq', COALESCE((SELECT MAX(id) FROM reservations), 1))")
    conn.commit()
    cur.close()
    conn.close()