from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from cipher import Franckate, Defranckate, FranckateSteps, DefranckateSteps, analyze_text
import secrets
import os
from datetime import datetime

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

# ── Config ────────────────────────────────────────────────
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "DATABASE_URL", "sqlite:///franckate.db"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-in-prod")

db = SQLAlchemy(app)

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",
)

# ── Models ────────────────────────────────────────────────
class Developer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    api_key = db.Column(db.String(64), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    requests_count = db.Column(db.Integer, default=0)

    def set_password(self, p):
        self.password_hash = generate_password_hash(p)

    def check_password(self, p):
        return check_password_hash(self.password_hash, p)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "api_key": self.api_key,
            "created_at": self.created_at.isoformat(),
            "requests_count": self.requests_count,
        }

class RequestLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    developer_id = db.Column(db.Integer, db.ForeignKey("developer.id"), nullable=True)
    endpoint = db.Column(db.String(50))
    input_length = db.Column(db.Integer)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    success = db.Column(db.Boolean, default=True)


# ── Auth decorator ────────────────────────────────────────
def require_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        key = request.headers.get("X-API-Key") or request.args.get("api_key")
        if not key:
            return jsonify(error="Missing API key. Pass it as X-API-Key header."), 401
        dev = Developer.query.filter_by(api_key=key, is_active=True).first()
        if not dev:
            return jsonify(error="Invalid or inactive API key."), 403
        # log & count
        dev.requests_count += 1
        log = RequestLog(
            developer_id=dev.id,
            endpoint=request.endpoint,
            input_length=len(str(request.get_json(silent=True) or {})),
            success=True,
        )
        db.session.add(log)
        db.session.commit()
        request.developer = dev
        return f(*args, **kwargs)
    return decorated


# ── Auth routes ───────────────────────────────────────────
@app.route("/api/register", methods=["POST"])
@limiter.limit("10 per hour")
def register():
    data = request.get_json()
    if not data:
        return jsonify(error="Request body required"), 400
    name = data.get("name", "").strip()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    if not name or not email or not password:
        return jsonify(error="name, email, and password are required"), 400
    if len(password) < 8:
        return jsonify(error="Password must be at least 8 characters"), 400
    if Developer.query.filter_by(email=email).first():
        return jsonify(error="Email already registered"), 409
    dev = Developer(
        name=name,
        email=email,
        api_key=secrets.token_urlsafe(32),
    )
    dev.set_password(password)
    db.session.add(dev)
    db.session.commit()
    return jsonify(
        message="Registration successful! Save your API key — it won't be shown again.",
        developer=dev.to_dict(),
    ), 201


@app.route("/api/login", methods=["POST"])
@limiter.limit("20 per hour")
def login():
    data = request.get_json()
    if not data:
        return jsonify(error="Request body required"), 400
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    dev = Developer.query.filter_by(email=email).first()
    if not dev or not dev.check_password(password):
        return jsonify(error="Invalid email or password"), 401
    return jsonify(developer=dev.to_dict()), 200


@app.route("/api/me", methods=["GET"])
@require_api_key
def me():
    return jsonify(developer=request.developer.to_dict())


@app.route("/api/regenerate-key", methods=["POST"])
@limiter.limit("5 per hour")
def regenerate_key():
    data = request.get_json()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    dev = Developer.query.filter_by(email=email).first()
    if not dev or not dev.check_password(password):
        return jsonify(error="Invalid credentials"), 401
    dev.api_key = secrets.token_urlsafe(32)
    db.session.commit()
    return jsonify(message="New API key generated", api_key=dev.api_key)


# ── Cipher routes ─────────────────────────────────────────
@app.route("/api/encrypt", methods=["POST"])
@require_api_key
@limiter.limit("500 per hour")
def encrypt():
    data = request.get_json()
    if not data or "text" not in data:
        return jsonify(error="'text' field is required"), 400
    text = data["text"]
    if len(text) > 10_000:
        return jsonify(error="Input too long. Max 10,000 characters."), 413
    encrypted = Franckate(text)
    return jsonify(
        original=text,
        encrypted=encrypted,
        length={"input": len(text), "output": len(encrypted)},
        algorithm="franckate-v1",
    )


@app.route("/api/decrypt", methods=["POST"])
@require_api_key
@limiter.limit("500 per hour")
def decrypt():
    data = request.get_json()
    if not data or "text" not in data:
        return jsonify(error="'text' field is required"), 400
    text = data["text"]
    if len(text) > 50_000:
        return jsonify(error="Input too long."), 413
    try:
        decrypted = Defranckate(text)
    except Exception as e:
        return jsonify(error=f"Decryption failed: invalid franckate ciphertext. {str(e)}"), 422
    return jsonify(
        original=text,
        decrypted=decrypted,
        algorithm="franckate-v1",
    )


@app.route("/api/encrypt/steps", methods=["POST"])
@require_api_key
@limiter.limit("200 per hour")
def encrypt_steps():
    """Returns a character-by-character breakdown for learning."""
    data = request.get_json()
    if not data or "text" not in data:
        return jsonify(error="'text' field is required"), 400
    text = data["text"]
    if len(text) > 200:
        return jsonify(error="Steps mode max 200 characters."), 413
    steps = FranckateSteps(text)
    encrypted = Franckate(text)
    return jsonify(
        original=text,
        encrypted=encrypted,
        steps=steps,
        total_steps=len(steps),
        algorithm="franckate-v1",
    )


@app.route("/api/decrypt/steps", methods=["POST"])
@require_api_key
@limiter.limit("200 per hour")
def decrypt_steps():
    data = request.get_json()
    if not data or "text" not in data:
        return jsonify(error="'text' field is required"), 400
    text = data["text"]
    if len(text) > 2000:
        return jsonify(error="Steps mode max 2000 characters of ciphertext."), 413
    steps = DefranckateSteps(text)
    decrypted = Defranckate(text)
    return jsonify(
        original=text,
        decrypted=decrypted,
        steps=steps,
        total_steps=len(steps),
        algorithm="franckate-v1",
    )


@app.route("/api/batch/encrypt", methods=["POST"])
@require_api_key
@limiter.limit("100 per hour")
def batch_encrypt():
    data = request.get_json()
    if not data or "texts" not in data:
        return jsonify(error="'texts' array is required"), 400
    texts = data["texts"]
    if not isinstance(texts, list):
        return jsonify(error="'texts' must be an array"), 400
    if len(texts) > 50:
        return jsonify(error="Max 50 items per batch"), 400
    results = []
    for i, text in enumerate(texts):
        if not isinstance(text, str):
            results.append({"index": i, "error": "Item must be a string"})
            continue
        if len(text) > 10_000:
            results.append({"index": i, "error": "Item too long (max 10,000 chars)"})
            continue
        results.append({
            "index": i,
            "original": text,
            "encrypted": Franckate(text),
        })
    return jsonify(results=results, count=len(results), algorithm="franckate-v1")


@app.route("/api/batch/decrypt", methods=["POST"])
@require_api_key
@limiter.limit("100 per hour")
def batch_decrypt():
    data = request.get_json()
    if not data or "texts" not in data:
        return jsonify(error="'texts' array is required"), 400
    texts = data["texts"]
    if not isinstance(texts, list):
        return jsonify(error="'texts' must be an array"), 400
    if len(texts) > 50:
        return jsonify(error="Max 50 items per batch"), 400
    results = []
    for i, text in enumerate(texts):
        if not isinstance(text, str):
            results.append({"index": i, "error": "Item must be a string"})
            continue
        try:
            results.append({
                "index": i,
                "original": text,
                "decrypted": Defranckate(text),
            })
        except Exception as e:
            results.append({"index": i, "error": str(e)})
    return jsonify(results=results, count=len(results), algorithm="franckate-v1")


@app.route("/api/analyze", methods=["POST"])
@require_api_key
@limiter.limit("200 per hour")
def analyze():
    """Analyze text to show character category distribution."""
    data = request.get_json()
    if not data or "text" not in data:
        return jsonify(error="'text' field is required"), 400
    text = data["text"]
    if len(text) > 10_000:
        return jsonify(error="Input too long."), 413
    return jsonify(analysis=analyze_text(text), algorithm="franckate-v1")


# ── Public info ───────────────────────────────────────────
@app.route("/api/info", methods=["GET"])
def info():
    return jsonify(
        name="Franckate Cipher API",
        version="1.0.0",
        description="A substitution cipher that encodes each character as a category prefix + position index.",
        algorithm="franckate-v1",
        categories={
            "U": "Uppercase letters (A-Z → U0. to U25.)",
            "L": "Lowercase letters (a-z → L0. to L25.)",
            "D": "Digits (0-9 → D0. to D9.)",
            "F": "Special characters and space → F0. to F27.",
        },
        endpoints=[
            "POST /api/encrypt",
            "POST /api/decrypt",
            "POST /api/encrypt/steps",
            "POST /api/decrypt/steps",
            "POST /api/batch/encrypt",
            "POST /api/batch/decrypt",
            "POST /api/analyze",
        ],
        auth="X-API-Key header or ?api_key= query param",
        docs="https://franckate.vercel.app",
    )


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify(status="ok", timestamp=datetime.utcnow().isoformat())


# ── Init ──────────────────────────────────────────────────
with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=False, port=5000)
