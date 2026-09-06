from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from google import genai
from dotenv import load_dotenv
from sqlalchemy.exc import IntegrityError
from sqlalchemy import inspect, text
from urllib.parse import quote_plus
from datetime import datetime
from pathlib import Path
import csv
import json, re, traceback, os

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")
if not app.secret_key:
    raise RuntimeError("FLASK_SECRET_KEY must be set in the .env file.")

# Database Setup
database_url = os.getenv("DATABASE_URL")

# Use DATABASE_URL when it is provided (for example, on deployment). Locally,
# build the MySQL connection string from the existing MYSQL_* values in .env.
if not database_url:
    mysql_user = os.getenv("MYSQL_USER")
    mysql_password = os.getenv("MYSQL_PASSWORD")
    mysql_host = os.getenv("MYSQL_HOST")
    mysql_database = os.getenv("MYSQL_DATABASE")
    mysql_port = os.getenv("MYSQL_PORT", "3306")

    if not all([mysql_user, mysql_password, mysql_host, mysql_database]):
        raise RuntimeError("Set DATABASE_URL or the MYSQL_* database settings in the .env file.")

    database_url = (
        f"mysql+pymysql://{quote_plus(mysql_user)}:{quote_plus(mysql_password)}"
        f"@{mysql_host}:{mysql_port}/{mysql_database}"
    )

# Render's DATABASE_URL may start with postgres://
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# Gemini Setup (Updated for 2026 Model Availability)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY)

# Use the current 2026 stable model
MODEL = "gemini-2.5-flash" 

# Database Models
class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, nullable=False, default=False, server_default=text("0"))

    trips = db.relationship("Trip", back_populates="user", lazy=True)


class State(db.Model):
    """Indian state or union territory that contains one or more cities."""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    code = db.Column(db.String(10), unique=True)
    description = db.Column(db.Text)

    cities = db.relationship("City", back_populates="state", lazy=True)
    destinations = db.relationship("Destination", back_populates="state", lazy=True)


class Destination(db.Model):
    """A travel destination stored under one state."""
    id = db.Column(db.Integer, primary_key=True)
    state_id = db.Column(db.Integer, db.ForeignKey("state.id"), nullable=False)
    name = db.Column(db.String(150), nullable=False)
    region = db.Column(db.String(50), nullable=False)
    category = db.Column(db.String(80), nullable=False)
    popular_attraction_name = db.Column(db.String(150), nullable=False)
    accessibility = db.Column(db.String(50), nullable=False)
    nearest_airport = db.Column(db.String(150), nullable=False)
    nearest_railway_station = db.Column(db.String(150), nullable=False)

    __table_args__ = (
        db.UniqueConstraint("state_id", "name", name="uq_destination_state_name"),
    )

    state = db.relationship("State", back_populates="destinations")


class City(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    state_id = db.Column(db.Integer, db.ForeignKey("state.id"), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    country = db.Column(db.String(100), nullable=False, default="India")
    description = db.Column(db.Text)

    __table_args__ = (
        db.UniqueConstraint("state_id", "name", name="uq_city_state_name"),
    )

    state = db.relationship("State", back_populates="cities")
    attractions = db.relationship("Attraction", back_populates="city", lazy=True)
    hotels = db.relationship("Hotel", back_populates="city", lazy=True)
    restaurants = db.relationship("Restaurant", back_populates="city", lazy=True)
    trips = db.relationship("Trip", back_populates="city", lazy=True)


class Attraction(db.Model):
    """A tourist attraction stored under one city."""
    id = db.Column(db.Integer, primary_key=True)
    city_id = db.Column(db.Integer, db.ForeignKey("city.id"), nullable=False)
    name = db.Column(db.String(150), nullable=False)
    category = db.Column(db.String(80), nullable=False)
    description = db.Column(db.Text)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    opening_time = db.Column(db.Time)
    closing_time = db.Column(db.Time)
    average_visit_duration = db.Column(db.Integer)
    entry_fee = db.Column(db.Float, default=0.0)
    rating = db.Column(db.Float)
    image_url = db.Column(db.String(500))

    city = db.relationship("City", back_populates="attractions")


class Hotel(db.Model):
    """Accommodation option stored under one city."""
    id = db.Column(db.Integer, primary_key=True)
    city_id = db.Column(db.Integer, db.ForeignKey("city.id"), nullable=False)
    hotel_name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text)
    address = db.Column(db.String(255))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    price_range = db.Column(db.String(50))
    rating = db.Column(db.Float)
    contact_number = db.Column(db.String(30))
    website = db.Column(db.String(500))
    amenities = db.Column(db.Text)
    image_url = db.Column(db.String(500))

    city = db.relationship("City", back_populates="hotels")


class Restaurant(db.Model):
    """Dining option stored under one city."""
    id = db.Column(db.Integer, primary_key=True)
    city_id = db.Column(db.Integer, db.ForeignKey("city.id"), nullable=False)
    restaurant_name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text)
    cuisine = db.Column(db.String(100))
    address = db.Column(db.String(255))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    average_cost_for_two = db.Column(db.Float)
    opening_time = db.Column(db.Time)
    closing_time = db.Column(db.Time)
    vegetarian_available = db.Column(db.Boolean, default=False)
    rating = db.Column(db.Float)
    contact_number = db.Column(db.String(30))
    website = db.Column(db.String(500))
    image_url = db.Column(db.String(500))

    city = db.relationship("City", back_populates="restaurants")


class Trip(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    city_id = db.Column(db.Integer, db.ForeignKey("city.id"), nullable=False)
    trip_name = db.Column(db.String(150), nullable=False)
    days = db.Column(db.Integer, nullable=False)
    budget_level = db.Column(db.String(50))
    travel_style = db.Column(db.String(80))
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    user = db.relationship("User", back_populates="trips")
    city = db.relationship("City", back_populates="trips")


DESTINATION_IMPORT_COLUMNS = [
    "Destination Name",
    "State",
    "Region",
    "Category",
    "Popular Attraction",
    "Accessibility",
    "Nearest Airport",
    "Nearest Railway Station",
]
DESTINATION_IMPORT_CSV = Path(__file__).resolve().parent / "data" / "Expanded_Indian_Travel_Dataset.csv"


def import_destination_csv():
    """Import the fixed project destination CSV using the existing database session."""
    summary = {
        "rows_read": 0,
        "duplicate_rows_skipped": 0,
        "new_states_created": 0,
        "new_destinations_created": 0,
        "existing_destinations_skipped": 0,
    }
    seen_rows = set()

    try:
        with DESTINATION_IMPORT_CSV.open(encoding="utf-8-sig", newline="") as csv_file:
            reader = csv.DictReader(csv_file)
            if reader.fieldnames != DESTINATION_IMPORT_COLUMNS:
                raise ValueError(f"Unexpected CSV columns: {reader.fieldnames}")

            for row in reader:
                summary["rows_read"] += 1
                row_key = tuple(row[column] for column in DESTINATION_IMPORT_COLUMNS)
                if row_key in seen_rows:
                    summary["duplicate_rows_skipped"] += 1
                    continue
                seen_rows.add(row_key)

                state_name = (row["State"] or "").strip()
                destination_name = (row["Destination Name"] or "").strip()
                state = State.query.filter_by(name=state_name).first()
                if state is None:
                    state = State(name=state_name)
                    db.session.add(state)
                    db.session.flush()
                    summary["new_states_created"] += 1

                destination = Destination.query.filter_by(
                    state_id=state.id,
                    name=destination_name,
                ).first()
                if destination is not None:
                    summary["existing_destinations_skipped"] += 1
                    continue

                db.session.add(Destination(
                    state_id=state.id,
                    name=destination_name,
                    region=(row["Region"] or "").strip(),
                    category=(row["Category"] or "").strip(),
                    popular_attraction_name=(row["Popular Attraction"] or "").strip(),
                    accessibility=(row["Accessibility"] or "").strip(),
                    nearest_airport=(row["Nearest Airport"] or "").strip(),
                    nearest_railway_station=(row["Nearest Railway Station"] or "").strip(),
                ))
                summary["new_destinations_created"] += 1

        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    summary["total_destinations"] = Destination.query.count()
    return summary


def migrate_user_password_column():
    """Move passwords from the old users table to secure password hashes once."""
    columns = {column["name"] for column in inspect(db.engine).get_columns("users")}

    if "password_hash" in columns:
        return

    # The old student-project table used a plain-text `password` column.
    # Add the new column, hash any existing passwords, then remove the old one.
    with db.engine.begin() as connection:
        connection.execute(text("ALTER TABLE users ADD COLUMN password_hash VARCHAR(255) NULL"))

        if "password" in columns:
            old_users = connection.execute(text("SELECT id, password FROM users")).mappings()
            for old_user in old_users:
                connection.execute(
                    text("UPDATE users SET password_hash = :password_hash WHERE id = :id"),
                    {
                        "id": old_user["id"],
                        "password_hash": generate_password_hash(old_user["password"]),
                    },
                )

            connection.execute(text("ALTER TABLE users DROP COLUMN password"))

        connection.execute(text("ALTER TABLE users MODIFY COLUMN password_hash VARCHAR(255) NOT NULL"))


def migrate_user_admin_column():
    """Add the administrator flag to existing users tables once."""
    columns = {column["name"] for column in inspect(db.engine).get_columns("users")}
    if "is_admin" not in columns:
        with db.engine.begin() as connection:
            connection.execute(
                text("ALTER TABLE users ADD COLUMN is_admin BOOLEAN NOT NULL DEFAULT FALSE")
            )


def migrate_city_unique_constraint():
    """Add the city/state uniqueness rule to existing database tables once."""
    inspector = inspect(db.engine)
    unique_constraints = inspector.get_unique_constraints("city")
    if any(constraint.get("name") == "uq_city_state_name" for constraint in unique_constraints):
        return

    with db.engine.begin() as connection:
        connection.execute(
            text("ALTER TABLE city ADD CONSTRAINT uq_city_state_name UNIQUE (state_id, name)")
        )


with app.app_context():
    try:
        print("Creating database tables...")
        db.create_all()
        migrate_user_password_column()
        migrate_user_admin_column()
        migrate_city_unique_constraint()
        print("Database tables created successfully!")
    except Exception as e:
        print("ERROR CREATING TABLES:", e)
        raise

# Auth Routes
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    email = data.get("email", "").strip().lower()
    password = data.get("password", "").strip()
    user = User.query.filter_by(email=email).first()
    if user and check_password_hash(user.password_hash, password):
        session["user_email"] = email
        session["user_name"] = user.name
        return jsonify({"success": True, "user": {"name": user.name, "email": email}})
    return jsonify({"success": False, "message": "Invalid email or password."})

@app.route("/signup", methods=["POST"])
def signup():
    data = request.get_json(silent=True) or {}
    name = data.get("name", "").strip()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "").strip()

    if not name:
        return jsonify({"success": False, "message": "Please enter your name."})
    if not email:
        return jsonify({"success": False, "message": "Please enter your email."})

    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        return jsonify({"success": False, "message": "Email already registered."})
    if len(password) < 6:
        return jsonify({"success": False, "message": "Password must be at least 6 characters."})

    new_user = User(
        name=name,
        email=email,
        password_hash=generate_password_hash(password)
    )
    db.session.add(new_user)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"success": False, "message": "Email already registered."})

    session["user_email"] = email
    session["user_name"] = name
    return jsonify({"success": True, "user": {"name": name, "email": email}})

@app.route("/planner")
def planner():
    if "user_email" not in session:
        return redirect(url_for("index"))
    return render_template("planner.html",
                           user_name=session["user_name"],
                           user_email=session["user_email"])


@app.route("/admin")
def admin_dashboard():
    """Show the dashboard only to an existing administrator account."""
    email = session.get("user_email")
    if not email:
        return redirect(url_for("index"))

    user = User.query.filter_by(email=email).first()
    if user is None or not user.is_admin:
        return "Admin access required.", 403

    counts = {
        "users": User.query.count(),
        "states": State.query.count(),
        "cities": City.query.count(),
        "destinations": Destination.query.count(),
        "attractions": Attraction.query.count(),
    }
    return render_template("admin.html", admin_name=user.name, counts=counts)


@app.route("/admin/import-destinations", methods=["POST"])
def admin_import_destinations():
    """Run the fixed project destination importer for an administrator."""
    email = session.get("user_email")
    if not email:
        return redirect(url_for("index"))

    user = User.query.filter_by(email=email).first()
    if user is None or not user.is_admin:
        return "Admin access required.", 403

    try:
        summary = import_destination_csv()
        flash(
            "Import completed successfully.\n\n"
            f"Rows read: {summary['rows_read']}\n"
            f"Duplicate rows skipped: {summary['duplicate_rows_skipped']}\n"
            f"New states created: {summary['new_states_created']}\n"
            f"New destinations created: {summary['new_destinations_created']}\n"
            f"Existing destinations skipped: {summary['existing_destinations_skipped']}\n"
            f"Total destinations: {summary['total_destinations']}",
            "success",
        )
    except (OSError, ValueError, IntegrityError) as error:
        flash(f"Import failed: {error}", "error")

    return redirect(url_for("admin_dashboard"))


@app.route("/admin/destinations", methods=["GET", "POST"])
def manage_destinations():
    """Allow administrators to add, edit, and delete destination records."""
    email = session.get("user_email")
    if not email:
        return redirect(url_for("index"))

    user = User.query.filter_by(email=email).first()
    if user is None or not user.is_admin:
        return "Admin access required.", 403

    if request.method == "POST":
        action = request.form.get("action")

        if action == "delete":
            destination = db.session.get(
                Destination, request.form.get("destination_id", type=int)
            )
            if destination is None:
                flash("Destination not found.", "error")
            else:
                try:
                    db.session.delete(destination)
                    db.session.commit()
                    flash("Destination deleted.", "success")
                except IntegrityError:
                    db.session.rollback()
                    flash("Destination could not be deleted because another record depends on it.", "error")
            return redirect(url_for("manage_destinations"))

        values = {
            "name": request.form.get("name", "").strip(),
            "region": request.form.get("region", "").strip(),
            "category": request.form.get("category", "").strip(),
            "popular_attraction_name": request.form.get("popular_attraction_name", "").strip(),
            "accessibility": request.form.get("accessibility", "").strip(),
            "nearest_airport": request.form.get("nearest_airport", "").strip(),
            "nearest_railway_station": request.form.get("nearest_railway_station", "").strip(),
        }
        state = db.session.get(State, request.form.get("state_id", type=int))

        if not state or not all(values.values()):
            flash("Please complete every destination field and choose a valid state.", "error")
            return redirect(url_for("manage_destinations"))

        destination_id = request.form.get("destination_id", type=int)
        destination = db.session.get(Destination, destination_id) if destination_id else None
        if action == "update" and destination is None:
            flash("Destination not found.", "error")
            return redirect(url_for("manage_destinations"))

        duplicate = Destination.query.filter(
            Destination.state_id == state.id,
            db.func.lower(Destination.name) == values["name"].lower(),
        ).first()
        if duplicate and duplicate.id != destination_id:
            flash("That destination already exists in the selected state.", "error")
            return redirect(url_for("manage_destinations"))

        if action == "create":
            destination = Destination(state_id=state.id, **values)
            db.session.add(destination)
            success_message = "Destination added."
        elif action == "update":
            destination.state_id = state.id
            for field, value in values.items():
                setattr(destination, field, value)
            success_message = "Destination updated."
        else:
            flash("Unknown form action.", "error")
            return redirect(url_for("manage_destinations"))

        try:
            db.session.commit()
            flash(success_message, "success")
        except IntegrityError:
            db.session.rollback()
            flash("That destination already exists in the selected state.", "error")
        return redirect(url_for("manage_destinations"))

    editing_destination = None
    edit_id = request.args.get("edit", type=int)
    if edit_id:
        editing_destination = db.session.get(Destination, edit_id)
        if editing_destination is None:
            flash("Destination not found.", "error")
            return redirect(url_for("manage_destinations"))

    destinations = Destination.query.join(State).order_by(
        State.name, Destination.name
    ).all()
    states = State.query.order_by(State.name).all()
    return render_template(
        "admin_destinations.html",
        admin_name=user.name,
        destinations=destinations,
        states=states,
        editing_destination=editing_destination,
    )


@app.route("/admin/cities", methods=["GET", "POST"])
def manage_cities():
    """Allow administrators to add, edit, and safely delete cities."""
    email = session.get("user_email")
    if not email:
        return redirect(url_for("index"))

    user = User.query.filter_by(email=email).first()
    if user is None or not user.is_admin:
        return "Admin access required.", 403

    if request.method == "POST":
        action = request.form.get("action")

        if action == "delete":
            city = db.session.get(City, request.form.get("city_id", type=int))
            if city is None:
                flash("City not found.", "error")
            else:
                dependencies = []
                if Attraction.query.filter_by(city_id=city.id).count():
                    dependencies.append("attractions")
                if Hotel.query.filter_by(city_id=city.id).count():
                    dependencies.append("hotels")
                if Restaurant.query.filter_by(city_id=city.id).count():
                    dependencies.append("restaurants")
                if Trip.query.filter_by(city_id=city.id).count():
                    dependencies.append("trips")

                if dependencies:
                    flash(
                        f"City cannot be deleted because it has dependent {', '.join(dependencies)}.",
                        "error",
                    )
                else:
                    try:
                        db.session.delete(city)
                        db.session.commit()
                        flash("City deleted.", "success")
                    except IntegrityError:
                        db.session.rollback()
                        flash("City could not be deleted because another record depends on it.", "error")
            return redirect(url_for("manage_cities"))

        name = request.form.get("name", "").strip()
        country = request.form.get("country", "").strip()
        description = request.form.get("description", "").strip() or None
        state = db.session.get(State, request.form.get("state_id", type=int))

        if not state or not name or not country:
            flash("Please provide a city name, state, and country.", "error")
            return redirect(url_for("manage_cities"))

        city_id = request.form.get("city_id", type=int)
        city = db.session.get(City, city_id) if city_id else None
        if action == "update" and city is None:
            flash("City not found.", "error")
            return redirect(url_for("manage_cities"))

        duplicate = City.query.filter(
            City.state_id == state.id,
            db.func.lower(City.name) == name.lower(),
        ).first()
        if duplicate and duplicate.id != city_id:
            flash("That city already exists in the selected state.", "error")
            return redirect(url_for("manage_cities"))

        if action == "create":
            city = City(state_id=state.id, name=name, country=country, description=description)
            db.session.add(city)
            success_message = "City added."
        elif action == "update":
            city.state_id = state.id
            city.name = name
            city.country = country
            city.description = description
            success_message = "City updated."
        else:
            flash("Unknown form action.", "error")
            return redirect(url_for("manage_cities"))

        try:
            db.session.commit()
            flash(success_message, "success")
        except IntegrityError:
            db.session.rollback()
            flash("That city already exists in the selected state.", "error")
        return redirect(url_for("manage_cities"))

    editing_city = None
    edit_id = request.args.get("edit", type=int)
    if edit_id:
        editing_city = db.session.get(City, edit_id)
        if editing_city is None:
            flash("City not found.", "error")
            return redirect(url_for("manage_cities"))

    cities = City.query.join(State).order_by(State.name, City.name).all()
    states = State.query.order_by(State.name).all()
    return render_template(
        "admin_cities.html",
        admin_name=user.name,
        cities=cities,
        states=states,
        editing_city=editing_city,
    )


@app.route("/admin/attractions", methods=["GET", "POST"])
def manage_attractions():
    """Allow administrators to add, edit, and delete attraction records."""
    email = session.get("user_email")
    if not email:
        return redirect(url_for("index"))

    user = User.query.filter_by(email=email).first()
    if user is None or not user.is_admin:
        return "Admin access required.", 403

    if request.method == "POST":
        action = request.form.get("action")

        if action == "delete":
            attraction = db.session.get(
                Attraction, request.form.get("attraction_id", type=int)
            )
            if attraction is None:
                flash("Attraction not found.", "error")
            else:
                try:
                    db.session.delete(attraction)
                    db.session.commit()
                    flash("Attraction deleted.", "success")
                except IntegrityError:
                    db.session.rollback()
                    flash("Attraction could not be deleted because another record depends on it.", "error")
            return redirect(url_for("manage_attractions"))

        name = request.form.get("name", "").strip()
        category = request.form.get("category", "").strip()
        city = db.session.get(City, request.form.get("city_id", type=int))
        if not name or not category or not city:
            flash("Please provide an attraction name, category, and city.", "error")
            return redirect(url_for("manage_attractions"))

        try:
            duration_text = request.form.get("average_visit_duration", "").strip()
            duration = int(duration_text) if duration_text else None
            if duration is not None and duration < 1:
                raise ValueError("Visit duration must be a positive whole number.")

            entry_fee_text = request.form.get("entry_fee", "").strip()
            entry_fee = float(entry_fee_text) if entry_fee_text else 0.0
            if entry_fee < 0:
                raise ValueError("Entry fee cannot be negative.")

            rating_text = request.form.get("rating", "").strip()
            rating = float(rating_text) if rating_text else None
            if rating is not None and not 0 <= rating <= 5:
                raise ValueError("Rating must be between 0 and 5.")

            latitude_text = request.form.get("latitude", "").strip()
            longitude_text = request.form.get("longitude", "").strip()
            if bool(latitude_text) != bool(longitude_text):
                raise ValueError("Provide both latitude and longitude, or leave both blank.")
            latitude = float(latitude_text) if latitude_text else None
            longitude = float(longitude_text) if longitude_text else None
            if latitude is not None and not -90 <= latitude <= 90:
                raise ValueError("Latitude must be between -90 and 90.")
            if longitude is not None and not -180 <= longitude <= 180:
                raise ValueError("Longitude must be between -180 and 180.")

            opening_text = request.form.get("opening_time", "").strip()
            closing_text = request.form.get("closing_time", "").strip()
            opening_time = datetime.strptime(opening_text, "%H:%M").time() if opening_text else None
            closing_time = datetime.strptime(closing_text, "%H:%M").time() if closing_text else None
        except ValueError as error:
            flash(str(error), "error")
            return redirect(url_for("manage_attractions"))

        attraction_id = request.form.get("attraction_id", type=int)
        attraction = db.session.get(Attraction, attraction_id) if attraction_id else None
        if action == "update" and attraction is None:
            flash("Attraction not found.", "error")
            return redirect(url_for("manage_attractions"))

        duplicate = Attraction.query.filter(
            Attraction.city_id == city.id,
            db.func.lower(Attraction.name) == name.lower(),
        ).first()
        if duplicate and duplicate.id != attraction_id:
            flash("That attraction already exists in the selected city.", "error")
            return redirect(url_for("manage_attractions"))

        values = {
            "city_id": city.id,
            "name": name,
            "category": category,
            "latitude": latitude,
            "longitude": longitude,
            "opening_time": opening_time,
            "closing_time": closing_time,
            "average_visit_duration": duration,
            "entry_fee": entry_fee,
            "rating": rating,
            "image_url": request.form.get("image_url", "").strip() or None,
        }
        if action == "create":
            attraction = Attraction(**values)
            db.session.add(attraction)
            success_message = "Attraction added."
        elif action == "update":
            for field, value in values.items():
                setattr(attraction, field, value)
            success_message = "Attraction updated."
        else:
            flash("Unknown form action.", "error")
            return redirect(url_for("manage_attractions"))

        try:
            db.session.commit()
            flash(success_message, "success")
        except IntegrityError:
            db.session.rollback()
            flash("That attraction already exists in the selected city.", "error")
        return redirect(url_for("manage_attractions"))

    editing_attraction = None
    edit_id = request.args.get("edit", type=int)
    if edit_id:
        editing_attraction = db.session.get(Attraction, edit_id)
        if editing_attraction is None:
            flash("Attraction not found.", "error")
            return redirect(url_for("manage_attractions"))

    attractions = Attraction.query.join(City).order_by(City.name, Attraction.name).all()
    cities = City.query.join(State).order_by(State.name, City.name).all()
    return render_template(
        "admin_attractions.html",
        admin_name=user.name,
        attractions=attractions,
        cities=cities,
        editing_attraction=editing_attraction,
    )

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


@app.route("/api/destination-suggestions")
def destination_suggestions():
    """Return matching destination names for the planner input."""
    if "user_email" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"suggestions": []})

    matches = Destination.query.filter(
        db.func.lower(Destination.name).like(f"%{query.lower()}%")
    ).order_by(db.func.lower(Destination.name)).limit(40).all()

    suggestions = []
    seen_names = set()
    for destination in matches:
        name_key = destination.name.casefold()
        if name_key not in seen_names:
            suggestions.append(destination.name)
            seen_names.add(name_key)
        if len(suggestions) == 8:
            break

    return jsonify({"suggestions": suggestions})


@app.route("/api/transport-info")
def transport_info():
    """Return stored transport reference information for one destination."""
    if "user_email" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    destination_name = request.args.get("destination", "").strip()
    if not destination_name:
        return jsonify({"error": "Please choose a destination."}), 400

    destination = Destination.query.filter(
        db.func.lower(Destination.name) == destination_name.lower()
    ).order_by(Destination.id).first()
    if destination is None:
        return jsonify({"error": "No transport information is available for that destination."}), 404

    return jsonify({
        "destination": {
            "name": destination.name,
            "state": destination.state.name,
            "nearest_airport": destination.nearest_airport,
            "nearest_railway_station": destination.nearest_railway_station,
        }
    })


@app.route("/api/cities-for-state")
def cities_for_state():
    """Return stored cities and their travel highlights for a selected state."""
    if "user_email" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    state_name = request.args.get("state", "").strip()
    if not state_name:
        return jsonify({"error": "Please enter a state name."}), 400

    state = State.query.filter(
        db.func.lower(State.name) == state_name.lower()
    ).first()
    if not state:
        return jsonify({"error": f"No travel data is available for {state_name} yet."}), 404

    cities = []
    for city in state.cities:
        specialties = sorted({
            attraction.category for attraction in city.attractions if attraction.category
        })[:4]
        cities.append({
            "id": city.id,
            "name": city.name,
            "description": city.description or "Explore this city and its local experiences.",
            "specialties": specialties,
            "attractions": [attraction.name for attraction in city.attractions[:4]],
        })

    return jsonify({"success": True, "state": state.name, "cities": cities})


def select_itinerary_attractions(attractions, interests, limit=6):
    """Prefer attraction categories related to selected interests, then rating."""
    interest_categories = {
        "history": {"history", "heritage", "architecture", "museum", "cultural", "religious"},
        "adventure": {"adventure"},
        "nature": {"nature", "natural", "wildlife", "park", "garden", "beach"},
        "beaches": {"beach", "nature", "natural"},
        "shopping": {"shopping", "market"},
        "photography": {"photography", "architecture", "nature", "natural"},
    }
    preferred_categories = set()
    for interest in interests:
        preferred_categories.update(interest_categories.get(interest.lower(), set()))

    ordered_attractions = sorted(
        attractions,
        key=lambda attraction: (
            attraction.category.lower() not in preferred_categories,
            -(attraction.rating if attraction.rating is not None else -1),
            attraction.name.lower(),
        ),
    )

    selected = []
    seen_ids = set()
    for attraction in ordered_attractions:
        if attraction.id in seen_ids:
            continue
        seen_ids.add(attraction.id)

        attraction_data = {
            "name": attraction.name,
            "category": attraction.category,
        }
        if attraction.description:
            attraction_data["description"] = attraction.description
        if attraction.latitude is not None:
            attraction_data["latitude"] = attraction.latitude
        if attraction.longitude is not None:
            attraction_data["longitude"] = attraction.longitude
        if attraction.opening_time:
            attraction_data["opening_time"] = attraction.opening_time.strftime("%H:%M")
        if attraction.closing_time:
            attraction_data["closing_time"] = attraction.closing_time.strftime("%H:%M")
        if attraction.average_visit_duration is not None:
            attraction_data["average_visit_duration_minutes"] = attraction.average_visit_duration
        if attraction.entry_fee is not None:
            attraction_data["entry_fee"] = attraction.entry_fee
        if attraction.rating is not None:
            attraction_data["rating"] = attraction.rating
        if attraction.image_url:
            attraction_data["image_url"] = attraction.image_url
        selected.append(attraction_data)

        if len(selected) == limit:
            break

    return selected


def build_itinerary_travel_context(destination_name, interests):
    """Return only verified database facts for an exact destination match."""
    destination = Destination.query.filter(
        db.func.lower(Destination.name) == destination_name.lower()
    ).order_by(Destination.id).first()
    if destination is None:
        return None

    context = {
        "destination": {
            "name": destination.name,
            "state": destination.state.name,
            "region": destination.region,
            "category": destination.category,
            "accessibility": destination.accessibility,
            "popular_attraction_name": destination.popular_attraction_name,
            "nearest_airport": destination.nearest_airport,
            "nearest_railway_station": destination.nearest_railway_station,
        }
    }

    city = City.query.filter(
        City.state_id == destination.state_id,
        db.func.lower(City.name) == destination.name.lower(),
    ).first()
    if city:
        context["matching_city"] = {
            "name": city.name,
            "country": city.country,
        }
        attractions = Attraction.query.filter_by(city_id=city.id).all()
        selected_attractions = select_itinerary_attractions(attractions, interests)
        if selected_attractions:
            context["verified_attractions"] = selected_attractions

    return context


# Generate itinerary options
@app.route("/api/generate-itinerary", methods=["POST"])
def generate_itinerary():
    if "user_email" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    d = request.get_json(silent=True) or {}
    destination = d.get("destination", "")
    days = int(d.get("days", 3))
    travelers_value = d.get("travelers", 1)
    try:
        travelers = int(travelers_value)
    except (TypeError, ValueError):
        return jsonify({"success": False, "error": "Number of travelers must be a whole number."}), 400
    if isinstance(travelers_value, float) and not travelers_value.is_integer():
        return jsonify({"success": False, "error": "Number of travelers must be a whole number."}), 400
    if travelers < 1:
        return jsonify({"success": False, "error": "Number of travelers must be at least 1."}), 400

    budget = d.get("budget", "moderate")
    interests = d.get("interests", [])
    travel_style = d.get("travel_style", "balanced")
    currency = d.get("currency", "INR")
    interests_str = ', '.join(interests) if interests else 'general sightseeing'
    travel_context = build_itinerary_travel_context(destination, interests)
    verified_data_section = ""
    if travel_context:
        verified_data_section = (
            "\nVerified PlanGo Travel Data:\n"
            f"{json.dumps(travel_context, ensure_ascii=False, indent=2)}\n"
            "Treat this section as factual database information. Do not change or contradict it. "
            "Do not invent missing database fields. Use verified attractions when they are provided. "
            "If information is not provided, make clear it is an AI suggestion rather than verified PlanGo data. "
            "Do not claim that a hotel, restaurant, ticket price, weather condition, or transport availability "
            "is verified unless it appears in this section.\n"
        )

    prompt = (
        f"Create exactly 3 different but related {days}-day travel itinerary options for {destination}.\n"
        f"Number of travelers: {travelers}.\n"
        f"Budget: {budget}, Interests: {interests_str}, Style: {travel_style}, Currency: {currency}.\n"
        + verified_data_section
        + "Keep the same destination, trip length, travelers, budget, interests, travel style, "
        "currency, and verified database context in every option. Make the options meaningfully "
        "different in pacing, activities, daily structure, free time, and emphasis on selected interests. "
        "Do not create unrelated trips. Return only a valid JSON object with an 'options' array containing "
        "exactly 3 objects. Each option must have 'title' (string), 'description' (string), and 'itinerary' "
        "(object). The itinerary object must use this structure: 'destination' (string), 'duration' (number), "
        "'overview' (string), 'estimated_budget' (object with accommodation, food, activities, transport, and total), "
        "'weather_info' (string), 'days' (array). Each day must contain 'day' (number), 'theme' (string), "
        "'morning', 'afternoon', and 'evening' objects. Each activity object must have activity, description, "
        "duration, and cost as strings. Each day must also have 'meals' (object with breakfast, lunch, dinner) "
        "and 'tips' (string). Include 'packing_list' (object containing arrays), 'local_tips' (array of strings), "
        "'must_try_foods' (array of strings), 'emergency_info' (object), and 'best_time_to_visit' (string)."
    )

    try:
        response = client.models.generate_content(
            model=MODEL,
            contents=[{"role": "user", "parts": [{"text": prompt}]}],
            config={'response_mime_type': 'application/json'}
        )
        result = json.loads(response.text)
        options = result.get("options") if isinstance(result, dict) else None
        valid_options = []
        if isinstance(options, list):
            for option in options:
                if not isinstance(option, dict):
                    continue
                itinerary = option.get("itinerary")
                if isinstance(itinerary, dict) and isinstance(itinerary.get("days"), list):
                    valid_options.append({
                        "title": str(option.get("title") or f"Option {len(valid_options) + 1}"),
                        "description": str(option.get("description") or "A different way to plan this trip."),
                        "itinerary": itinerary,
                    })
                if len(valid_options) == 3:
                    break
        if len(valid_options) != 3:
            return jsonify({
                "success": False,
                "error": "The travel planner did not return three complete itinerary options. Please try again."
            }), 502
        return jsonify({"success": True, "options": valid_options})

    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)})

# AI: Travel Chat
@app.route("/api/chat", methods=["POST"])
def travel_chat():
    if "user_email" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    d = request.get_json()
    message = d.get("message", "")
    context = d.get("context", "")

    prompt = (
        "You are PlanGo AI, a helpful travel assistant.\n"
        + (f"Context: {context}\n" if context else "")
        + f"User: {message}\nReply in a friendly, helpful way."
    )

    try:
        response = client.models.generate_content(
            model=MODEL,
            contents=[{"role": "user", "parts": [{"text": prompt}]}]
        )
        reply = response.text.strip()
        return jsonify({"success": True, "reply": reply})

    except Exception as e:
        # If the model name is still wrong, list available models in the terminal
        print("\n--- ERROR: Model Not Found. Checking available models for your API key: ---")
        try:
            for m in client.models.list():
                print(f"- {m.name}")
        except:
            print("Could not list models. Check your API key.")
        
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
