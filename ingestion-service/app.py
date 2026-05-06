import time
import requests
import psycopg2
import os


# -----------------------------
# DB CONNECTION
# -----------------------------
def connect_db():
    while True:
        try:
            conn = psycopg2.connect(
                host=os.getenv("DB_HOST"),
                database=os.getenv("DB_NAME"),
                user=os.getenv("DB_USER"),
                password=os.getenv("DB_PASSWORD")
            )
            print("✅ Connected to DB")
            return conn
        except Exception as e:
            print("⏳ Waiting for DB...", e)
            time.sleep(2)


# -----------------------------
# CREATE TABLES
# -----------------------------
def create_tables(conn):
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS btc_data (
            id SERIAL PRIMARY KEY,
            price FLOAT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS eth_data (
            id SERIAL PRIMARY KEY,
            price FLOAT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS xrp_data (
            id SERIAL PRIMARY KEY,
            price FLOAT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    conn.commit()
    cursor.close()
    print("✅ Tables ready")


# -----------------------------
# FETCH DATA
# -----------------------------
def fetch_prices():
    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {
        "ids": "bitcoin,ethereum,ripple",
        "vs_currencies": "usd"
    }

    response = requests.get(url, params=params)
    data = response.json()

    return {
        "BTC": data["bitcoin"]["usd"],
        "ETH": data["ethereum"]["usd"],
        "XRP": data["ripple"]["usd"]
    }


# -----------------------------
# INSERT DATA
# -----------------------------
def insert_price(conn, table, price):
    cursor = conn.cursor()

    cursor.execute(
        f"INSERT INTO {table} (price) VALUES (%s)",
        (float(price),)
    )

    # keep last 1000 rows
    cursor.execute(f"""
        DELETE FROM {table}
        WHERE id NOT IN (
            SELECT id FROM {table}
            ORDER BY timestamp DESC
            LIMIT 1000
        )
    """)

    conn.commit()
    cursor.close()


# -----------------------------
# MAIN PROCESS
# -----------------------------
def process():
    print("🚀 Ingestion service is running...")

    conn = connect_db()
    create_tables(conn)

    while True:
        try:
            prices = fetch_prices()
            print("📊 Prices:", prices)

            insert_price(conn, "btc_data", prices["BTC"])
            insert_price(conn, "eth_data", prices["ETH"])
            insert_price(conn, "xrp_data", prices["XRP"])

            time.sleep(60)

        except Exception as e:
            print("❌ Error:", e)
            conn.rollback()
            time.sleep(5)


if __name__ == "__main__":
    process()