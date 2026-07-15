from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from google import genai
from dotenv import load_dotenv
import json, re, traceback, os

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")
if not app.secret_key:
    raise RuntimeError("FLASK_SECRET_KEY must be set in the .env file.")

# Database Setup
# Keep MySQL settings in .env so the password is not hardcoded in this file.
# Database Setup (Render PostgreSQL)
database_url = os.getenv("DATABASE_URL")

if not database_url:
    raise RuntimeError("DATABASE_URL environment variable is not set.")

# Render's DATABASE_URL may start with postgres://
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
with app.app_context():
    try:
        print("Creating database tables...")
        db.create_all()
        print("Database tables created successfully!")
    except Exception as e:
        print("ERROR CREATING TABLES:", e)
        raise

# Gemini Setup (Updated for 2026 Model Availability)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY)

# Use the current 2026 stable model
MODEL = "gemini-2.5-flash" 

# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    trips = db.relationship("Trip", back_populates="user", lazy=True)


class State(db.Model):
    """Indian state or union territory that contains one or more cities."""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    code = db.Column(db.String(10), unique=True)
    description = db.Column(db.Text)

    cities = db.relationship("City", back_populates="state", lazy=True)


class City(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    state_id = db.Column(db.Integer, db.ForeignKey("state.id"), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    country = db.Column(db.String(100), nullable=False, default="India")
    description = db.Column(db.Text)

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
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    city_id = db.Column(db.Integer, db.ForeignKey("city.id"), nullable=False)
    trip_name = db.Column(db.String(150), nullable=False)
    days = db.Column(db.Integer, nullable=False)
    budget_level = db.Column(db.String(50))
    travel_style = db.Column(db.String(80))
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    user = db.relationship("User", back_populates="trips")
    city = db.relationship("City", back_populates="trips")


def create_tables():
    """Create database tables for Phase 1 if they do not already exist."""
    with app.app_context():
        db.create_all()

# Auth Routes
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
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
    data = request.get_json()
    name = data.get("name", "").strip()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "").strip()
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
    db.session.commit()

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

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


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


# AI: Generate Itinerary
@app.route("/api/generate-itinerary", methods=["POST"])
def generate_itinerary():
    if "user_email" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    d = request.get_json()
    destination = d.get("destination", "")
    days = int(d.get("days", 3))
    budget = d.get("budget", "moderate")
    interests = d.get("interests", [])
    travel_style = d.get("travel_style", "balanced")
    currency = d.get("currency", "INR")
    interests_str = ', '.join(interests) if interests else 'general sightseeing'

    prompt = (
        f"Create a detailed {days}-day travel itinerary for {destination}.\n"
        f"Budget: {budget}, Interests: {interests_str}, Style: {travel_style}, Currency: {currency}.\n"
        "Return only a valid JSON object using this exact structure: "
        "'destination' (string), 'duration' (number), 'overview' (string), "
        "'estimated_budget' (object with accommodation, food, activities, transport, and total), "
        "'weather_info' (string), 'days' (array). Each day must contain 'day' (number), "
        "'theme' (string), 'morning', 'afternoon', and 'evening' objects. Each activity object "
        "must have activity, description, duration, and cost as strings. Each day must also have "
        "'meals' (object with breakfast, lunch, dinner) and 'tips' (string). Include "
        "'packing_list' (object containing arrays), 'local_tips' (array of strings), "
        "'must_try_foods' (array of strings), 'emergency_info' (object), and "
        "'best_time_to_visit' (string)."
    )

    try:
        response = client.models.generate_content(
            model=MODEL,
            contents=[{"role": "user", "parts": [{"text": prompt}]}],
            config={'response_mime_type': 'application/json'}
        )
        result = json.loads(response.text)
        return jsonify({"success": True, "itinerary": result})

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
    create_tables()
    app.run(debug=True, port=5000)
