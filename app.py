from flask import Flask, render_template, jsonify, request, Response
import csv
from io import StringIO
import psycopg2
import os
from datetime import datetime, timedelta

app = Flask(__name__)

START_TIME = datetime.now()
LAST_SEEN = None

DATABASE_URL = os.environ.get("DATABASE_URL")
def get_db():
    return psycopg2.connect(DATABASE_URL)


def init_db():

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS logs (
        id SERIAL PRIMARY KEY,
        timestamp TIMESTAMP,
        temperature REAL,
        current REAL,
        count INTEGER,
        power REAL,
        machine_status VARCHAR(20)
    )
    """)

    conn.commit()
    cur.close()
    conn.close()


@app.route("/")
def dashboard():
    return render_template("dashboard.html")


@app.route("/api/stats")
def stats():

    uptime = (datetime.now() - START_TIME).total_seconds()

    return jsonify({
        "uptime_seconds": int(uptime)
    })


@app.route("/api/latest")
def latest_data():

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT *
        FROM logs
        ORDER BY id DESC
        LIMIT 1
    """)

    row = cur.fetchone()

    if not row:
        cur.close()
        conn.close()
        return jsonify({})
    
        global LAST_SEEN

    if LAST_SEEN:
        diff = (datetime.now() - LAST_SEEN).total_seconds()

        if diff > 10:
            cur.close()
            conn.close()
            return jsonify({
                "machine_status": "OFFLINE"
            })

    columns = [desc[0] for desc in cur.description]

    result = dict(zip(columns, row))

    cur.close()
    conn.close()

    return jsonify(result)


@app.route("/api/history")
def history():

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT *
        FROM logs
        ORDER BY id DESC
        LIMIT 100
    """)

    rows = cur.fetchall()

    columns = [desc[0] for desc in cur.description]

    data = [
        dict(zip(columns, row))
        for row in rows
    ]

    cur.close()
    conn.close()

    return jsonify(data)


@app.route("/api/history/filter")
def history_filter():

    start = request.args.get("start")
    end = request.args.get("end")

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT *
        FROM logs
        WHERE timestamp BETWEEN %s AND %s
        ORDER BY id DESC
    """, (start, end))

    rows = cur.fetchall()

    columns = [desc[0] for desc in cur.description]

    data = [
        dict(zip(columns, row))
        for row in rows
    ]

    cur.close()
    conn.close()

    return jsonify(data)


@app.route("/api/data", methods=["POST"])
def receive_data():

    data = request.get_json(silent=True)

    if not data:
        return jsonify({
            "status": "error",
            "message": "Invalid JSON"
        }), 400

    print("ESP DATA:", data)

    temperature = float(data.get("temperature", 0))
    current = float(data.get("current", 0))
    count = int(data.get("count", 0))

    power = round(current * 230, 2)

    if current == -1:
        status = "DISABLED"
    elif current > 0.5:
        status = "RUNNING"
    else:
        status = "STOPPED"
    timestamp = datetime.now()
    global LAST_SEEN
    LAST_SEEN = timestamp

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO logs
        (
            timestamp,
            temperature,
            current,
            count,
            power,
            machine_status
        )
        VALUES (%s,%s,%s,%s,%s,%s)
    """, (
        timestamp,
        temperature,
        current,
        count,
        power,
        status
    ))

    # keep only last 7 days
    cur.execute("""
        DELETE FROM logs
        WHERE timestamp < NOW() - INTERVAL '7 days'
    """)

    conn.commit()

    cur.close()
    conn.close()

    return jsonify({
        "status": "ok"
    })


@app.route("/api/heartbeat")
def heartbeat():

    global LAST_SEEN

    if LAST_SEEN is None:
        return jsonify({"status": "OFFLINE"})

    diff = (datetime.now() - LAST_SEEN).total_seconds()

    if diff > 10:
        return jsonify({"status": "OFFLINE"})
    else:
        return jsonify({"status": "ONLINE"})

@app.route("/reset", methods=["POST"])
def reset_data():

    conn = get_db()
    cur = conn.cursor()

    cur.execute("DELETE FROM logs")

    conn.commit()

    cur.close()
    conn.close()

    return jsonify({
        "status": "success"
    })

@app.route("/api/export/csv")
def export_csv():

    start = request.args.get("start")
    end = request.args.get("end")

    conn = get_db()
    cur = conn.cursor()

    if start and end:

        start_dt = datetime.fromisoformat(start)
        end_dt = datetime.fromisoformat(end)

        cur.execute("""
            SELECT *
            FROM logs
            WHERE timestamp BETWEEN %s AND %s
            ORDER BY timestamp ASC
        """, (start_dt, end_dt))

    else:

        cur.execute("""
            SELECT *
            FROM logs
            ORDER BY timestamp ASC
        """)

    rows = cur.fetchall()

    print("ROWS FOUND:", len(rows))

    columns = [desc[0] for desc in cur.description]

    output = StringIO()
    writer = csv.writer(output)

    writer.writerow(columns)

    for row in rows:
        writer.writerow(row)

    cur.close()
    conn.close()

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={
            "Content-Disposition":
            "attachment; filename=machine_logs.csv"
        }
    )
init_db()

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 9000)),
        debug=False
    )