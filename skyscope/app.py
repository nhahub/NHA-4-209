import json
import os
import random
from functools import wraps

from ml.predictor import FlightDelayPredictor
from flask import (
    Flask,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

app = Flask(__name__)
app.secret_key = "skyscope-dev-secret-key-change-in-production"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
USERS_FILE = os.path.join(BASE_DIR, "data", "users.json")
FLIGHTS_FILE = os.path.join(BASE_DIR, "data", "flights.json")


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user" not in session:
            flash("Please log in to access SkyScope.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)

    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get("role") != "Admin":
            flash("Admin access required.", "danger")
            return redirect(url_for("dashboard"))
        return f(*args, **kwargs)

    return decorated


import time

_dashboard_stats_cache = {"data": None, "timestamp": 0}
DASHBOARD_CACHE_TTL = 600  # 10 دقايق

def format_number(n):
    if n is None:
        return "0"
    n = int(n)
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


def compute_dashboard_stats():
    now = time.time()
    if _dashboard_stats_cache["data"] and (now - _dashboard_stats_cache["timestamp"] < DASHBOARD_CACHE_TTL):
        return _dashboard_stats_cache["data"]

    row = run_query(
        """SELECT 
               COUNT(*) AS total_flights,
               SUM(CASE WHEN DepDelayMinutes > 0 THEN 1 ELSE 0 END) AS delayed_flights,
               SUM(CASE WHEN DepDelayMinutes = 0 THEN 1 ELSE 0 END) AS on_time_flights,
               ROUND(AVG(CASE WHEN DepDelayMinutes >= 0 THEN DepDelayMinutes END), 1) AS average_delay
           FROM flights"""
    )[0]

    stats = {
        "total_flights": format_number(row["total_flights"]),
        "delayed_flights": format_number(row["delayed_flights"]),
        "on_time_flights": format_number(row["on_time_flights"]),
        "average_delay": float(row["average_delay"]) if row["average_delay"] is not None else 0,
    }
    _dashboard_stats_cache["data"] = stats
    _dashboard_stats_cache["timestamp"] = now
    return stats

from database.db import run_query, run_write

SQL_QUERIES = {
    "total_flights": {
        "title": "Total Flights",
        "description": "Total number of flights in the dataset.",
        "columns": ["Total Flights"],
        "sql": "SELECT COUNT(*) AS Total_flights FROM flights",
    },
    "top_airline": {
        "title": "Top Airline by Flight Count",
        "description": "Airline with the highest number of flights.",
        "columns": ["Airline", "Total Flights"],
        "sql": """SELECT Airline, COUNT(*) AS Total_flights
                  FROM flights GROUP BY Airline
                  ORDER BY Total_flights DESC LIMIT 1""",
    },
    "avg_dep_delay": {
        "title": "Average Departure Delay",
        "description": "Average departure delay across completed flights.",
        "columns": ["Avg Dep Delay (min)"],
        "sql": """SELECT ROUND(AVG(DepDelayMinutes), 2) AS Avg_Dep_Delay
                  FROM flights WHERE DepDelayMinutes >= 0""",
    },
    "delayed_count": {
        "title": "Delayed Flights Count",
        "description": "Number of flights with a positive departure delay.",
        "columns": ["Delayed Flights"],
        "sql": "SELECT COUNT(*) AS Delayed_flights FROM flights WHERE DepDelayMinutes > 0",
    },
    "busiest_airport": {
        "title": "Busiest Departure Airport",
        "description": "Origin airport with the highest flight volume.",
        "columns": ["Origin", "Total Flights"],
        "sql": """SELECT Origin, COUNT(*) AS Total_flights
                  FROM flights WHERE FlightStatus IN ('Completed','Diverted')
                  GROUP BY Origin ORDER BY Total_flights DESC LIMIT 1""",
    },
    "avg_delay_airline": {
        "title": "Average Delay by Airline",
        "description": "Average departure delay minutes across all carriers.",
        "columns": ["Airline", "Avg Delay (min)"],
        "sql": """SELECT Airline, ROUND(AVG(DepDelayMinutes), 2) AS Avg_Delay
                  FROM flights WHERE DepDelayMinutes >= 0
                  GROUP BY Airline ORDER BY Avg_Delay DESC""",
    },
    "ontime_ranking": {
        "title": "On-Time Performance Ranking",
        "description": "Airlines ranked by on-time percentage.",
        "columns": ["Airline", "Total Flights", "On-Time Flights", "On-Time Rate", "Rank"],
        "sql": """SELECT Airline, COUNT(*) AS Total_flights,
                  SUM(CASE WHEN IsDelayed = 0 THEN 1 ELSE 0 END) AS OnTime_flights,
                  ROUND(SUM(CASE WHEN IsDelayed = 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS OnTime_Rate,
                  RANK() OVER (ORDER BY SUM(CASE WHEN IsDelayed = 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) DESC) AS Performance_Rank
                  FROM flights WHERE FlightStatus = 'Completed'
                  GROUP BY Airline ORDER BY Performance_Rank""",
    },
    "worst_routes": {
        "title": "Top 10 Worst Routes",
        "description": "Routes with the highest average arrival delay (min 1000 flights).",
        "columns": ["Route", "Total Flights", "Avg Arr Delay", "Avg Dep Delay", "Delayed Flights", "Delay Rate"],
        "sql": """SELECT CONCAT(Origin, ' → ', Dest) AS RouteKey, COUNT(*) AS Total_flights,
                  ROUND(AVG(ArrDelay), 2) AS Avg_Arr_Delay, ROUND(AVG(DepDelay), 2) AS Avg_Dep_Delay,
                  SUM(CASE WHEN IsDelayed = 1 THEN 1 ELSE 0 END) AS Delayed_flights,
                  ROUND(SUM(CASE WHEN IsDelayed = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS Delay_Rate
                  FROM flights WHERE FlightStatus = 'Completed'
                  GROUP BY Origin, Dest HAVING COUNT(*) > 1000
                  ORDER BY Avg_Arr_Delay DESC LIMIT 10""",
    },
}

def run_analytics_query(query_id):
    query_def = SQL_QUERIES[query_id]
    rows = run_query(query_def["sql"])
    return [list(row.values()) for row in rows]


@app.route("/")
def index():
    if "user" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        users = load_json(USERS_FILE)
        user = next((u for u in users if u["username"] == username and u["password"] == password), None)
        if user:
            session["user"] = user["username"]
            session["role"] = user["role"]
            session["full_name"] = user["full_name"]
            flash(f"Welcome back, {user['full_name']}!", "success")
            return redirect(url_for("dashboard"))
        flash("Invalid username or password.", "danger")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    stats = compute_dashboard_stats()
    return render_template("dashboard.html", stats=stats)


@app.route("/flights")
@login_required
def flights():
    return render_template("flights.html", is_admin=session.get("role") == "Admin")

ALLOWED_SORT_FIELDS = {
    "Flight_number": "Flight_Number_Operating_Airline",
    "Airline": "Airline",
    "Origin": "Origin",
    "Destination": "Dest",
    "Flight_date": "FlightDate",
    "Dep_time": "CRSDepTime",
    "Dep_delay": "DepDelayMinutes",
    "Arr_delay": "ArrDelay",
    "Status": "FlightStatus",
}


@app.route("/api/flights", methods=["GET"])
@login_required
def api_flights():
    page = max(int(request.args.get("page", 1)), 1)
    page_size = min(max(int(request.args.get("page_size", 8)), 1), 50)
    search = request.args.get("search", "").strip()
    status = request.args.get("status", "").strip()
    airline = request.args.get("airline", "").strip()
    sort = request.args.get("sort", "flight_date")
    direction = "DESC" if request.args.get("dir", "asc").lower() == "desc" else "ASC"
    sort_col = ALLOWED_SORT_FIELDS.get(sort, "FlightDate")

    where, params = [], []
    if search:
        like = f"{search}%"
        where.append("(Airline LIKE %s OR Origin LIKE %s OR Dest LIKE %s OR Flight_Number_Operating_Airline LIKE %s)")
        params += [like, like, like, like]
    if status:
        where.append("FlightStatus = %s")
        params.append(status)
    if airline:
        where.append("Airline = %s")
        params.append(airline)
    where_clause = f"WHERE {' AND '.join(where)}" if where else ""

    total = run_query(f"SELECT COUNT(*) AS cnt FROM flights {where_clause}", params)[0]["cnt"]
    offset = (page - 1) * page_size
    rows = run_query(
        f"""SELECT id, Flight_Number_Operating_Airline, Airline, Origin, Dest,
                   FlightDate, CRSDepTime, DepDelayMinutes, ArrDelay, FlightStatus
            FROM flights {where_clause}
            ORDER BY {sort_col} {direction}
            LIMIT %s OFFSET %s""",
        params + [page_size, offset],
    )
    return jsonify({"rows": rows, "total": total, "page": page, "page_size": page_size})


@app.route("/api/airlines")
@login_required
def api_airlines():
    rows = run_query("SELECT DISTINCT Airline FROM flights ORDER BY Airline")
    return jsonify([r["Airline"] for r in rows])


@app.route("/api/flights", methods=["POST"])
@login_required
@admin_required
def api_add_flight():
    data = request.get_json()
    result = run_write(
        """INSERT INTO flights (Flight_Number_Operating_Airline, Airline, Origin, Dest,
                                 FlightDate, CRSDepTime, DepDelayMinutes, ArrDelay, FlightStatus)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
        (
            data.get("flight_number"),
            data.get("airline"),
            data.get("origin", "").upper(),
            data.get("destination", "").upper(),
            data.get("flight_date"),
            data.get("dep_time"),
            data.get("dep_delay", 0),
            data.get("arr_delay", 0),
            data.get("status", "Completed"),
        ),
    )
    return jsonify({"id": result["lastrowid"]}), 201


@app.route("/api/flights/<int:flight_id>", methods=["PUT"])
@login_required
@admin_required
def api_update_flight(flight_id):
    data = request.get_json()
    run_write(
        """UPDATE flights SET Flight_Number_Operating_Airline=%s, Airline=%s, Origin=%s, Dest=%s,
                               FlightDate=%s, CRSDepTime=%s, DepDelayMinutes=%s, ArrDelay=%s, FlightStatus=%s
           WHERE id=%s""",
        (
            data.get("flight_number"),
            data.get("airline"),
            data.get("origin", "").upper(),
            data.get("destination", "").upper(),
            data.get("flight_date"),
            data.get("dep_time"),
            data.get("dep_delay", 0),
            data.get("arr_delay", 0),
            data.get("status", "Completed"),
            flight_id,
        ),
    )
    return jsonify({"success": True})


@app.route("/api/flights/<int:flight_id>", methods=["DELETE"])
@login_required
@admin_required
def api_delete_flight(flight_id):
    run_write("DELETE FROM flights WHERE id=%s", (flight_id,))
    return jsonify({"success": True})

@app.route("/api/flight/<int:flight_id>")
@login_required
@admin_required
def api_get_flight(flight_id):
    rows = run_query(
        """SELECT id, Flight_Number_Operating_Airline, Airline, Origin, Dest,
                  FlightDate, CRSDepTime, DepDelayMinutes, ArrDelay, FlightStatus
           FROM flights WHERE id = %s""",
        (flight_id,),
    )
    if not rows:
        return jsonify({"error": "Flight not found"}), 404
    return jsonify(rows[0])
    
@app.route("/analytics")
@login_required
def analytics():
    return render_template("analytics.html", queries=SQL_QUERIES)


@app.route("/api/analytics/<query_id>")
@login_required
def api_analytics(query_id):
    if query_id not in SQL_QUERIES:
        return jsonify({"error": "Unknown query"}), 404
    rows = run_analytics_query(query_id)
    return jsonify({"columns": SQL_QUERIES[query_id]["columns"], "rows": rows})

@app.route("/prediction")
@login_required
def prediction():
    try:
        options = FlightDelayPredictor.get_instance().get_form_options()
        model_ready = True
    except Exception as exc:
        options = {"airlines": [], "airports": [], "days_of_week": []}
        model_ready = False
        flash(f"ML models could not be loaded: {exc}", "warning")
    return render_template("prediction.html", **options, model_ready=model_ready)


@app.route("/api/predict", methods=["POST"])
@login_required
def api_predict():
    data = request.get_json() or {}
    try:
        result = FlightDelayPredictor.get_instance().predict(data)
        return jsonify(result)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": f"Prediction failed: {exc}"}), 500


@app.route("/users")
@login_required
@admin_required
def users():
    users_list = load_json(USERS_FILE)
    safe_users = [{k: v for k, v in u.items() if k != "password"} for u in users_list]
    return render_template("users.html", users=safe_users)


@app.route("/api/users", methods=["POST"])
@login_required
@admin_required
def api_add_user():
    users_list = load_json(USERS_FILE)
    data = request.get_json()
    if any(u["username"] == data["username"] for u in users_list):
        return jsonify({"error": "Username already exists"}), 400
    new_id = max((u["id"] for u in users_list), default=0) + 1
    user = {
        "id": new_id,
        "username": data["username"],
        "password": data["password"],
        "role": data.get("role", "User"),
        "email": data.get("email", ""),
        "full_name": data.get("full_name", data["username"]),
    }
    users_list.append(user)
    save_json(USERS_FILE, users_list)
    safe = {k: v for k, v in user.items() if k != "password"}
    return jsonify(safe), 201


@app.route("/api/users/<int:user_id>", methods=["DELETE"])
@login_required
@admin_required
def api_delete_user(user_id):
    users_list = load_json(USERS_FILE)
    user = next((u for u in users_list if u["id"] == user_id), None)
    if not user:
        return jsonify({"error": "User not found"}), 404
    if user["username"] == session.get("user"):
        return jsonify({"error": "Cannot delete your own account"}), 400
    users_list = [u for u in users_list if u["id"] != user_id]
    save_json(USERS_FILE, users_list)
    return jsonify({"success": True})


@app.route("/api/users/<int:user_id>/password", methods=["PUT"])
@login_required
@admin_required
def api_change_password(user_id):
    users_list = load_json(USERS_FILE)
    data = request.get_json()
    for i, u in enumerate(users_list):
        if u["id"] == user_id:
            users_list[i]["password"] = data["password"]
            save_json(USERS_FILE, users_list)
            return jsonify({"success": True})
    return jsonify({"error": "User not found"}), 404


if __name__ == "__main__":
    app.run(debug=True, port=5000)
