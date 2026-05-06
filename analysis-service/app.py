import time
import psycopg2
import os
import smtplib
from email.mime.text import MIMEText

# -----------------------------
# GLOBAL STATE
# -----------------------------
alert_state = {
    "BTC": "NORMAL",
    "ETH": "NORMAL",
    "XRP": "NORMAL"
}

last_alert_time = {
    "BTC": 0,
    "ETH": 0,
    "XRP": 0
}

COOLDOWN_SECONDS = 300  # 5 minutes


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
            print("✅ Connected to DB (analysis)")
            return conn
        except Exception as e:
            print("⏳ Waiting for DB...", e)
            time.sleep(2)


# -----------------------------
# CREATE ALERTS TABLE
# -----------------------------
def create_alerts_table(conn):
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id SERIAL PRIMARY KEY,
            coin VARCHAR(10),
            type VARCHAR(10),
            change FLOAT,
            message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    conn.commit()
    cursor.close()
    print("✅ Alerts table ready")


# -----------------------------
# SAVE ALERT
# -----------------------------
def save_alert(conn, coin, alert_type, change, message):
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO alerts (coin, type, change, message)
        VALUES (%s, %s, %s, %s)
    """, (coin, alert_type, change, message))

    conn.commit()
    cursor.close()


# -----------------------------
# GET LAST 2 PRICES
# -----------------------------
def get_last_two_prices(conn, table):
    cursor = conn.cursor()

    cursor.execute(f"""
        SELECT price FROM {table}
        ORDER BY timestamp DESC
        LIMIT 2
    """)

    rows = cursor.fetchall()
    cursor.close()

    if len(rows) < 2:
        return None, None

    return rows[0][0], rows[1][0]


# -----------------------------
# ANALYZE CHANGE
# -----------------------------
def analyze_change(latest, previous):
    if previous == 0:
        return 0

    return ((latest - previous) / previous) * 100


# -----------------------------
# EMAIL FUNCTION
# -----------------------------
def send_email(subject, message):
    sender = os.getenv("EMAIL_USER")
    password = os.getenv("EMAIL_PASS")
    receiver = os.getenv("EMAIL_TO")

    msg = MIMEText(message)
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = receiver

    try:
        print("📧 Attempting to send email...")
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender, password)
        server.send_message(msg)
        server.quit()
        print("📧 Email sent successfully")
    except Exception as e:
        print("❌ Email error:", e)


# -----------------------------
# SMART ALERT + COOLDOWN
# -----------------------------
def check_alert(conn, coin, change):
    global alert_state, last_alert_time

    current_time = time.time()

    print(f"DEBUG → {coin} change: {change:.5f}%")

    # 🚀 SPIKE
    if change > 3:
        if alert_state[coin] != "ALERT_UP":
            if current_time - last_alert_time[coin] > COOLDOWN_SECONDS:
                msg = f"{coin} SPIKE: {change:.2f}% → SELL"

                print("🚀", msg)
                send_email(f"{coin} SELL Alert", msg)
                save_alert(conn, coin, "SELL", change, msg)

                alert_state[coin] = "ALERT_UP"
                last_alert_time[coin] = current_time
            else:
                print(f"{coin} cooldown active")
        else:
            print(f"{coin} already in ALERT_UP")

    # 📉 DROP
    elif change < -3:
        if alert_state[coin] != "ALERT_DOWN":
            if current_time - last_alert_time[coin] > COOLDOWN_SECONDS:
                msg = f"{coin} DROP: {change:.2f}% → BUY"

                print("📉", msg)
                send_email(f"{coin} BUY Alert", msg)
                save_alert(conn, coin, "BUY", change, msg)

                alert_state[coin] = "ALERT_DOWN"
                last_alert_time[coin] = current_time
            else:
                print(f"{coin} cooldown active")
        else:
            print(f"{coin} already in ALERT_DOWN")

    # ✅ NORMAL
    else:
        if alert_state[coin] != "NORMAL":
            print(f"{coin} back to NORMAL")

        alert_state[coin] = "NORMAL"
        print(f"{coin} stable: {change:.2f}%")


# -----------------------------
# MAIN PROCESS
# -----------------------------
def process():
    print("📊 ANALYSIS SERVICE STARTED")

    conn = connect_db()
    create_alerts_table(conn)

    while True:
        try:
            for coin, table in {
                "BTC": "btc_data",
                "ETH": "eth_data",
                "XRP": "xrp_data"
            }.items():

                latest, previous = get_last_two_prices(conn, table)

                if latest is None:
                    print(f"Not enough data for {coin}")
                    continue

                change = analyze_change(latest, previous)
                check_alert(conn, coin, change)

            print("------")
            time.sleep(60)

        except Exception as e:
            print("❌ Error:", e)
            conn.rollback()
            time.sleep(5)


if __name__ == "__main__":
    process()