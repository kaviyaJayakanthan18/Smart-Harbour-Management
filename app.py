from flask import Flask, render_template, request, redirect, url_for, flash, session, send_from_directory
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
import os
import pandas as pd

APP_DB = "harbour_site.db"
BASE_RATE = 1000

app = Flask(__name__)
app.secret_key = "change-this-secret-for-production"

def get_db():
    conn = sqlite3.connect(APP_DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as con:
        con.execute("""
        CREATE TABLE IF NOT EXISTS ships (
            ship_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            arrival TEXT NOT NULL,
            departure TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        """)
        con.execute("""
        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ship_id TEXT NOT NULL,
            hours_docked INTEGER NOT NULL,
            service_cost REAL NOT NULL,
            base_rate REAL NOT NULL,
            total REAL NOT NULL,
            issued_at TEXT NOT NULL,
            FOREIGN KEY(ship_id) REFERENCES ships(ship_id)
        );
        """)
        con.execute("""
        CREATE TABLE IF NOT EXISTS circulars (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            filename TEXT,
            uploaded_at TEXT NOT NULL
        );
        """)
    print("DB initialized:", Path(APP_DB).resolve())

@app.before_request
def setup():
    if not hasattr(app, 'db_initialized'):
        init_db()
        os.makedirs(os.path.join(app.root_path, "uploads"), exist_ok=True)

        # os.makedirs("uploads", exist_ok=True)
        app.db_initialized = True

def is_logged_in():
    return session.get("logged_in", False)

def require_login(func):
    from functools import wraps
    @wraps(func)
    def wrapper(*a, **kw):
        if not is_logged_in():
            flash("Please login to access admin features.", "warning")
            return redirect(url_for("login", next=request.path))
        return func(*a, **kw)
    return wrapper

@app.route("/")
def home():
    now = datetime.now().isoformat(timespec="minutes")
    with get_db() as con:
        ship_count = con.execute("SELECT COUNT(*) as c FROM ships").fetchone()["c"]
        docked_count = con.execute("SELECT COUNT(*) as c FROM invoices").fetchone()["c"]
        next_arrivals = con.execute("SELECT * FROM ships WHERE arrival >= ? ORDER BY arrival LIMIT 5", (now,)).fetchall()
    return render_template("home.html", next_arrivals=next_arrivals, ship_count=ship_count, docked_count=docked_count, now=now)

@app.route("/schedules")
def schedules():
    with get_db() as con:
        ships = con.execute("SELECT * FROM ships ORDER BY arrival").fetchall()
    return render_template("schedules.html", ships=ships)

@app.route("/schedules/add", methods=["GET", "POST"])
@require_login
def add_ship():
    if request.method == "POST":
        ship_id = request.form.get("ship_id","").strip()
        name = request.form.get("name","").strip()
        arrival = request.form.get("arrival","").strip()
        departure = request.form.get("departure","").strip()
        if not (ship_id and name and arrival and departure):
            flash("All fields are required.", "danger")
            return redirect(url_for("add_ship"))
        try:
            a = datetime.fromisoformat(arrival)
            d = datetime.fromisoformat(departure)
            if d <= a:
                flash("Departure must be after arrival.", "danger")
                return redirect(url_for("add_ship"))
        except Exception:
            flash("Invalid date/time format.", "danger")
            return redirect(url_for("add_ship"))
        try:
            with get_db() as con:
                con.execute("INSERT INTO ships (ship_id, name, arrival, departure, created_at) VALUES (?, ?, ?, ?, ?)",
                            (ship_id, name, arrival, departure, datetime.now().isoformat(timespec="minutes")))
            update_ships_excel()
            flash(f"Ship {ship_id} added.", "success")
            return redirect(url_for("schedules"))
        except sqlite3.IntegrityError:
            flash("Ship ID already exists.", "danger")
            return redirect(url_for("add_ship"))
    return render_template("add_ship.html")

@app.route("/schedules/delete/<ship_id>", methods=["POST"])
@require_login
def delete_ship(ship_id):
    with get_db() as con:
        con.execute("DELETE FROM ships WHERE ship_id = ?", (ship_id,))
        con.execute("DELETE FROM invoices WHERE ship_id = ?", (ship_id,))
    flash(f"Ship {ship_id} and related invoices deleted.", "success")
    return redirect(url_for("schedules"))

@app.route("/fees", methods=["GET","POST"])
@require_login
def fees():
    if request.method == "POST":
        ship_id = request.form.get("ship_id","").strip()
        hours = request.form.get("hours","0").strip()
        service_cost = request.form.get("service_cost","0").strip()
        try:
            hours_i = int(hours)
            service_f = float(service_cost)
            if hours_i < 0 or service_f < 0:
                raise ValueError
        except ValueError:
            flash("Enter valid non-negative numeric values.", "danger")
            return redirect(url_for("fees"))
        with get_db() as con:
            ship = con.execute("SELECT * FROM ships WHERE ship_id = ?", (ship_id,)).fetchone()
            if not ship:
                flash("Ship not found. Add ship first.", "danger")
                return redirect(url_for("fees"))
            total = hours_i * BASE_RATE + service_f
            issued_at = datetime.now().isoformat(timespec="minutes")
            con.execute("""INSERT INTO invoices (ship_id, hours_docked, service_cost, base_rate, total, issued_at)
                           VALUES (?, ?, ?, ?, ?, ?)""", (ship_id, hours_i, service_f, BASE_RATE, total, issued_at))
        update_fees_excel()
        flash(f"Invoice created for {ship_id}: ₹{total:.2f}", "success")
        return redirect(url_for("invoices"))
    with get_db() as con:
        ships = con.execute("SELECT ship_id, name FROM ships ORDER BY name").fetchall()
    return render_template("fees.html", ships=ships, base_rate=BASE_RATE)

@app.route("/invoices")
def invoices():
    with get_db() as con:
        invoices = con.execute("SELECT * FROM invoices ORDER BY issued_at DESC").fetchall()
    return render_template("invoices.html", invoices=invoices)

@app.route("/invoices/delete/<int:inv_id>", methods=["POST"])
@require_login
def delete_invoice(inv_id):
    with get_db() as con:
        con.execute("DELETE FROM invoices WHERE id = ?", (inv_id,))
    flash(f"Invoice #{inv_id} deleted.", "success")
    return redirect(url_for("invoices"))

@app.route("/circulars", methods=["GET","POST"])
def circulars():
    if request.method == "POST":
        if not is_logged_in():
            flash("Login required to upload circulars.", "warning")
            return redirect(url_for("login"))
        title = request.form.get("title","").strip()
        file = request.files.get("file")
        if not title:
            flash("Title is required.", "danger")
            return redirect(url_for("circulars"))
        filename = None
        if file and file.filename:
            filename = f"{int(datetime.now().timestamp())}_{file.filename}"
            file.save(os.path.join("uploads", filename))
        with get_db() as con:
            con.execute("INSERT INTO circulars (title, filename, uploaded_at) VALUES (?, ?, ?)",
                        (title, filename, datetime.now().isoformat(timespec="minutes")))
        flash("Circular uploaded.", "success")
        return redirect(url_for("circulars"))
    with get_db() as con:
        circs = con.execute("SELECT * FROM circulars ORDER BY uploaded_at DESC").fetchall()
    return render_template("circulars.html", circs=circs)

@app.route("/uploads/<path:filename>")
def uploads(filename):
    return send_from_directory("uploads", filename, as_attachment=True)

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username","").strip()
        password = request.form.get("password","").strip()
        if username == "admin" and password == "harbour123":
            session["logged_in"] = True
            session["user"] = "admin"
            flash("Logged in as admin.", "success")
            nxt = request.args.get("next") or url_for("home")
            return redirect(nxt)
        flash("Invalid credentials.", "danger")
        return redirect(url_for("login"))
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out.", "info")
    return redirect(url_for("home"))

def update_ships_excel():
    with get_db() as con:
        ships = con.execute("SELECT ship_id, name, arrival, departure, created_at FROM ships ORDER BY arrival").fetchall()
        df = pd.DataFrame(ships)
        df.to_excel("ships.xlsx", index=False)

def update_fees_excel():
    with get_db() as con:
        invoices = con.execute("""
            SELECT invoices.id, ships.name, invoices.ship_id, invoices.hours_docked, invoices.service_cost, invoices.base_rate, invoices.total, invoices.issued_at
            FROM invoices
            JOIN ships ON invoices.ship_id = ships.ship_id
            ORDER BY invoices.issued_at DESC
        """).fetchall()
        df = pd.DataFrame(invoices)
        df.to_excel("fees.xlsx", index=False)

@app.route("/seed")
def seed_data():
    ship_names = [
        "Titanic", "Queen Mary", "USS Enterprise", "HMS Victory", "Yamato",
        "Bismarck", "USS Nautilus", "Seawise Giant", "Santa Maria", "Mayflower",
        "INS Vikramaditya", "INS Kolkata", "INS Kochi", "INS Chennai"
    ]
    conn = get_db()
    now = datetime.now()
    for idx, name in enumerate(ship_names):
        ship_id = f"BR{2000+idx}"
        arrival = (now + timedelta(days=idx)).isoformat(timespec="minutes")
        departure = (now + timedelta(days=idx, hours=8)).isoformat(timespec="minutes")
        try:
            conn.execute(
                "INSERT INTO ships (ship_id, name, arrival, departure, created_at) VALUES (?, ?, ?, ?, ?)",
                (ship_id, name, arrival, departure, now.isoformat(timespec="minutes"))
            )
        except sqlite3.IntegrityError:
            pass
    conn.commit()
    update_ships_excel()
    flash("Demo data seeded.", "success")
    return redirect(url_for("schedules"))

@app.route("/download/ships")
@require_login
def download_ships_excel():
    update_ships_excel()
    return send_from_directory('.', "ships.xlsx", as_attachment=True)

@app.route("/download/fees")
@require_login
def download_fees_excel():
    update_fees_excel()
    return send_from_directory('.', "fees.xlsx", as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True)