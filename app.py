import os
import uuid
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, session, jsonify
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
import cv2
import numpy as np

BASE_DIR = Path(__file__).parent
UPLOAD_FOLDER = BASE_DIR / "uploads"
UPLOAD_FOLDER.mkdir(exist_ok=True)

app = Flask(__name__, static_folder="static", template_folder="templates")
app.secret_key = os.environ.get("FLASK_SECRET", "dev-secret-change-me")

# DB config: use DATABASE_URL if set, else SQLite file
database_url = os.environ.get("DATABASE_URL") or f"sqlite:///{BASE_DIR / 'app.db'}"
app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# limit upload size (e.g., 500MB)
app.config["MAX_CONTENT_LENGTH"] = 500 * 1024 * 1024
app.config["UPLOAD_FOLDER"] = str(UPLOAD_FOLDER)

ALLOWED_EXT = {".mp4", ".mov", ".webm", ".ogg", ".mkv"}

db = SQLAlchemy(app)

# ---------- Models ----------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(300), nullable=False)

# ---------- Utilities ----------
def allowed_file(filename):
    ext = Path(filename).suffix.lower()
    return ext in ALLOWED_EXT

def save_upload(file_storage):
    filename = secure_filename(file_storage.filename)
    unique = f"{uuid.uuid4().hex}_{filename}"
    outpath = UPLOAD_FOLDER / unique
    file_storage.save(str(outpath))
    return unique, outpath

# sample frames (1 fps by default)
def sample_frames(video_path: Path, sample_rate=1.0):
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError("Cannot open video file")
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    interval = max(1, int(round(fps / sample_rate)))
    frames = []
    idx = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if idx % interval == 0:
            frames.append(frame.copy())
        idx += 1
    cap.release()
    return frames

def heuristic_deepfake_score(frames):
    # Very simple demo heuristic: based on average frame variance.
    if not frames:
        return {"score": 0.0, "reason": "no_frames"}
    variances = [float(np.var(cv2.cvtColor(f, cv2.COLOR_BGR2GRAY))) for f in frames]
    mean_var = float(np.mean(variances))
    score = (mean_var - 200.0) / 1000.0
    score = max(0.0, min(score, 1.0))
    return {"score": score, "reason": f"mean_var={mean_var:.2f}"}

# ---------- Routes ----------
@app.route("/")
def index():
    # When rendering Jinja templates, use render_template (do NOT serve HTML file directly).
    return render_template("index.html")

@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

@app.route("/analyze", methods=["POST"])
def analyze():
    if "video" not in request.files:
        return jsonify({"error": "No file part"}), 400
    f = request.files["video"]
    if f.filename == "":
        return jsonify({"error": "No selected file"}), 400
    if not allowed_file(f.filename):
        return jsonify({"error": "File type not allowed"}), 400

    unique_name, out_path = save_upload(f)
    try:
        frames = sample_frames(out_path, sample_rate=1.0)
        heur = heuristic_deepfake_score(frames)
        label = "Suspicious (deepfake suspected)" if heur["score"] > 0.5 else "Likely real"
        result = {"label": label, "score": heur["score"], "heuristic": heur, "video_url": url_for("uploaded_file", filename=unique_name)}
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ----- Auth -----
@app.route("/register", methods=["POST"])
def register():
    data = request.get_json(force=True)
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    if not username or not password:
        return jsonify({"msg": "username and password required"}), 400
    if User.query.filter_by(username=username).first():
        return jsonify({"msg": "username exists"}), 400
    u = User(username=username, password_hash=generate_password_hash(password))
    db.session.add(u)
    db.session.commit()
    return jsonify({"msg": "registered"})

@app.route("/login", methods=["POST"])
def login():
    data = request.get_json(force=True)
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    u = User.query.filter_by(username=username).first()
    if not u or not check_password_hash(u.password_hash, password):
        return jsonify({"msg": "invalid credentials"}), 401
    session["user_id"] = u.id
    return jsonify({"msg": "ok"})

# CLI helper to init DB
@app.cli.command("init-db")
def init_db():
    db.create_all()
    print("DB initialized.")

if __name__ == "__main__":
    # Create DB if not exists (for SQLite dev)
    if "sqlite" in database_url and not (BASE_DIR / "app.db").exists():
        db.create_all()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
