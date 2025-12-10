
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

def main():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL not set in environment or .env file")

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
    with open(schema_path, "r") as f:
        sql = f.read()
    cur.execute(sql)
    conn.commit()
    cur.close()
    conn.close()
    print("Database schema applied successfully.")

if __name__ == "__main__":
    main()
