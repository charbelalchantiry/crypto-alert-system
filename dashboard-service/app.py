from flask import Flask, render_template, request, jsonify
import psycopg2
import os

app = Flask(__name__)

# -----------------------------
# DB CONNECTION
# -----------------------------
def connect_db():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )

# -----------------------------
# MAIN DASHBOARD
# -----------------------------
@app.route("/")
def index():
    coin_filter = request.args.get("coin", "ALL")

    conn = connect_db()
    cursor = conn.cursor()

    # 🔹 Alerts
    if coin_filter != "ALL":
        cursor.execute("""
            SELECT coin, type, change, message, created_at
            FROM alerts
            WHERE coin = %s
            ORDER BY created_at DESC
            LIMIT 50
        """, (coin_filter,))
    else:
        cursor.execute("""
            SELECT coin, type, change, message, created_at
            FROM alerts
            ORDER BY created_at DESC
            LIMIT 50
        """)

    alerts = cursor.fetchall()

    # 🔹 Prices for charts
    def get_prices(table):
        cursor.execute(f"""
            SELECT price, timestamp
            FROM {table}
            ORDER BY timestamp DESC
            LIMIT 20
        """)
        return cursor.fetchall()[::-1]

    btc = get_prices("btc_data")
    eth = get_prices("eth_data")
    xrp = get_prices("xrp_data")

    cursor.close()
    conn.close()

    return render_template(
        "index.html",
        alerts=alerts,
        btc=btc,
        eth=eth,
        xrp=xrp,
        selected_coin=coin_filter
    )

# -----------------------------
# 🔴 LIVE PRICES API
# -----------------------------
@app.route("/api/prices")
def get_prices_api():
    conn = connect_db()
    cursor = conn.cursor()

    def get_data(table):
        cursor.execute(f"""
            SELECT price, timestamp
            FROM {table}
            ORDER BY timestamp DESC
            LIMIT 20
        """)
        return cursor.fetchall()[::-1]

    data = {
        "BTC": get_data("btc_data"),
        "ETH": get_data("eth_data"),
        "XRP": get_data("xrp_data")
    }

    cursor.close()
    conn.close()

    return jsonify(data)

# -----------------------------
# 🔔 LATEST ALERT API
# -----------------------------
@app.route("/api/latest-alert")
def latest_alert():
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT coin, type, change, message, created_at
        FROM alerts
        ORDER BY created_at DESC
        LIMIT 1
    """)

    alert = cursor.fetchone()

    cursor.close()
    conn.close()

    return jsonify({"alert": alert})

# -----------------------------
# ENTRY POINT
# -----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)