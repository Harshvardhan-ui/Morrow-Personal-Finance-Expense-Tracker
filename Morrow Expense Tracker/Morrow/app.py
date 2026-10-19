import os
import csv
from io import StringIO
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from dotenv import load_dotenv
from flask import Flask, flash, jsonify, make_response, redirect, render_template, request, url_for
from flask_login import LoginManager, UserMixin, current_user, login_required, login_user, logout_user
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from sqlalchemy import func
from werkzeug.security import check_password_hash, generate_password_hash

load_dotenv()
app = Flask(__name__, instance_relative_config=True)
is_production = os.getenv("APP_ENV") == "production"
secret_key = os.getenv("SECRET_KEY")
if is_production and not secret_key:
    raise RuntimeError("Set SECRET_KEY before starting in production.")
app.config["SECRET_KEY"] = secret_key or "local-development-key-change-before-deploy"
db_url = os.getenv("DATABASE_URL") or ("" if is_production else "sqlite:///expense_tracker.db")
if is_production and not db_url:
    raise RuntimeError("Set DATABASE_URL before starting in production.")
if db_url.startswith("mysql://"):
    db_url = db_url.replace("mysql://", "mysql+pymysql://", 1)
app.config["SQLALCHEMY_DATABASE_URI"] = db_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"pool_pre_ping": True}
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
if is_production:
    app.config["SESSION_COOKIE_SECURE"] = True

db = SQLAlchemy(app)
csrf = CSRFProtect(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message_category = "info"

CATEGORIES = ["Food & Dining", "Transport", "Shopping", "Bills", "Health", "Entertainment", "Travel", "Other"]
COMPANY_NAME = "Parihar Technologies"


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    expenses = db.relationship("Expense", backref="owner", cascade="all, delete-orphan", lazy=True)


class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    title = db.Column(db.String(120), nullable=False)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    category = db.Column(db.String(40), nullable=False)
    spent_on = db.Column(db.Date, nullable=False, index=True)
    note = db.Column(db.String(240), default="")


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


@app.context_processor
def inject_globals():
    return {"categories": CATEGORIES, "today": date.today(), "hour_now": datetime.now().hour,
            "company_name": COMPANY_NAME}


@app.get("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    return render_template("landing.html")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if not name or len(name) > 80 or "@" not in email or len(password) < 8:
            flash("Add your name, a valid email, and a password with at least 8 characters.", "error")
        elif User.query.filter_by(email=email).first():
            flash("That email already has an account. Try signing in.", "error")
        else:
            user = User(name=name, email=email, password_hash=generate_password_hash(password))
            db.session.add(user)
            db.session.commit()
            login_user(user)
            return redirect(url_for("dashboard"))
    return render_template("auth.html", mode="signup")


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user, remember=bool(request.form.get("remember")))
            return redirect(url_for("dashboard"))
        flash("Email or password didn’t match. Please try again.", "error")
    return render_template("auth.html", mode="login")


@app.post("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))


def month_bounds(month_value):
    try:
        start = datetime.strptime(month_value, "%Y-%m").date().replace(day=1)
    except (ValueError, TypeError):
        start = date.today().replace(day=1)
    end = date(start.year + (start.month == 12), start.month % 12 + 1, 1)
    return start, end


def month_summary(user_id, start, end):
    rows = (db.session.query(Expense.category, func.sum(Expense.amount))
            .filter(Expense.user_id == user_id, Expense.spent_on >= start, Expense.spent_on < end)
            .group_by(Expense.category).order_by(func.sum(Expense.amount).desc()).all())
    total = sum((Decimal(str(value)) for _, value in rows), Decimal("0.00"))
    daily_rows = (db.session.query(Expense.spent_on, func.sum(Expense.amount))
                  .filter(Expense.user_id == user_id, Expense.spent_on >= start, Expense.spent_on < end)
                  .group_by(Expense.spent_on).all())
    daily = {day.isoformat(): float(amount) for day, amount in daily_rows}
    return total, rows, daily


@app.get("/dashboard")
@login_required
def dashboard():
    month = request.args.get("month", date.today().strftime("%Y-%m"))
    start, end = month_bounds(month)
    total, category_rows, daily = month_summary(current_user.id, start, end)
    expenses = (Expense.query.filter(Expense.user_id == current_user.id, Expense.spent_on >= start, Expense.spent_on < end)
                .order_by(Expense.spent_on.desc(), Expense.id.desc()).all())
    previous_start = date(start.year - (start.month == 1), 12 if start.month == 1 else start.month - 1, 1)
    previous_end = start
    previous_total, _, _ = month_summary(current_user.id, previous_start, previous_end)
    change = None if previous_total == 0 else round(float((total - previous_total) / previous_total * 100), 1)
    return render_template("dashboard.html", month=start.strftime("%Y-%m"), month_label=start.strftime("%B %Y"),
                           total=total, expenses=expenses, category_rows=category_rows, daily=daily,
                           previous_total=previous_total, change=change, expense_count=len(expenses))


@app.get("/transactions")
@login_required
def transactions_page():
    expenses = (Expense.query.filter_by(user_id=current_user.id)
                .order_by(Expense.spent_on.desc(), Expense.id.desc()).all())
    total = sum((expense.amount for expense in expenses), Decimal("0.00"))
    return render_template("pages.html", page="transactions", page_title="Transactions",
                           page_description="Your complete spending history, organized in one place.",
                           expenses=expenses, total=total, expense_count=len(expenses))


@app.get("/reports")
@login_required
def reports_page():
    month = request.args.get("month", date.today().strftime("%Y-%m"))
    start, end = month_bounds(month)
    total, category_rows, daily = month_summary(current_user.id, start, end)
    expenses = (Expense.query.filter(Expense.user_id == current_user.id,
                                     Expense.spent_on >= start, Expense.spent_on < end)
                .order_by(Expense.spent_on.desc(), Expense.id.desc()).all())
    return render_template("pages.html", page="reports", page_title="Monthly reports",
                           page_description="Understand your spending patterns and export a report when you need one.",
                           month=start.strftime("%Y-%m"), month_label=start.strftime("%B %Y"),
                           total=total, category_rows=category_rows, daily=daily, expenses=expenses,
                           expense_count=len(expenses))


@app.get("/about")
@login_required
def about_page():
    return render_template("pages.html", page="about", page_title="About Morrow",
                           page_description="A clearer, calmer way to understand your personal spending.")


@app.post("/expenses")
@login_required
def add_expense():
    title = request.form.get("title", "").strip()
    category = request.form.get("category", "")
    spent_on = request.form.get("spent_on", "")
    note = request.form.get("note", "").strip()
    try:
        amount = Decimal(request.form.get("amount", "")).quantize(Decimal("0.01"))
        expense_date = datetime.strptime(spent_on, "%Y-%m-%d").date()
    except (InvalidOperation, ValueError):
        flash("Enter a valid amount and date.", "error")
        return redirect(url_for("dashboard"))
    if not title or len(title) > 120 or amount <= 0 or amount > Decimal("9999999999.99") or category not in CATEGORIES:
        flash("Check the expense name, amount, and category.", "error")
        return redirect(url_for("dashboard"))
    db.session.add(Expense(user_id=current_user.id, title=title, amount=amount, category=category,
                           spent_on=expense_date, note=note[:240]))
    db.session.commit()
    flash("Expense added.", "success")
    return redirect(url_for("dashboard", month=expense_date.strftime("%Y-%m")))


@app.post("/expenses/<int:expense_id>/delete")
@login_required
def delete_expense(expense_id):
    expense = Expense.query.filter_by(id=expense_id, user_id=current_user.id).first_or_404()
    month = expense.spent_on.strftime("%Y-%m")
    db.session.delete(expense)
    db.session.commit()
    flash("Expense removed.", "success")
    return redirect(url_for("dashboard", month=month))


@app.get("/api/monthly-summary")
@login_required
def monthly_summary_api():
    month = request.args.get("month", date.today().strftime("%Y-%m"))
    start, end = month_bounds(month)
    total, rows, daily = month_summary(current_user.id, start, end)
    return jsonify({"month": start.strftime("%Y-%m"), "total": float(total),
                    "categories": [{"name": category, "amount": float(amount)} for category, amount in rows],
                    "daily": daily})


@app.get("/reports/monthly.csv")
@login_required
def monthly_csv():
    month = request.args.get("month", date.today().strftime("%Y-%m"))
    start, end = month_bounds(month)
    expenses = (Expense.query.filter(Expense.user_id == current_user.id, Expense.spent_on >= start, Expense.spent_on < end)
                .order_by(Expense.spent_on.asc(), Expense.id.asc()).all())
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow([f"Monthly expense report — {start.strftime('%B %Y')}"])
    writer.writerow(["Date", "Description", "Category", "Note", "Amount"])
    for expense in expenses:
        writer.writerow([expense.spent_on.isoformat(), expense.title, expense.category, expense.note or "", f"{expense.amount:.2f}"])
    writer.writerow([])
    writer.writerow(["Total", "", "", "", f"{sum((e.amount for e in expenses), Decimal('0.00')):.2f}"])
    response = make_response("\ufeff" + output.getvalue())
    response.headers["Content-Type"] = "text/csv; charset=utf-8"
    response.headers["Content-Disposition"] = f"attachment; filename=morrow-{start:%Y-%m}-report.csv"
    return response


@app.get("/health")
def health():
    return {"status": "ok"}


with app.app_context():
    db.create_all()


if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG", "0") == "1")
