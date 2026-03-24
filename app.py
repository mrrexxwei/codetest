import os
import re
import json
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Allow requests from the WebPad frontend

SUBMISSIONS_DIR = "submissions"
os.makedirs(SUBMISSIONS_DIR, exist_ok=True)


def slugify(name: str) -> str:
    """Convert a name to a safe filename slug, e.g. 'Jane Smith' -> 'jane_smith'."""
    name = name.strip().lower()
    name = re.sub(r"[^\w\s-]", "", name)   # remove special chars
    name = re.sub(r"[\s-]+", "_", name)     # spaces/hyphens -> underscore
    return name or "unknown"


def unique_filepath(base_slug: str) -> str:
    """Return a unique filepath, appending _2, _3 etc. if the file already exists."""
    path = os.path.join(SUBMISSIONS_DIR, f"{base_slug}.json")
    if not os.path.exists(path):
        return path
    counter = 2
    while True:
        path = os.path.join(SUBMISSIONS_DIR, f"{base_slug}_{counter}.json")
        if not os.path.exists(path):
            return path
        counter += 1


@app.route("/submit", methods=["POST"])
def submit():
    # ── Parse body ──────────────────────────────────────────
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 415

    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Invalid or empty JSON body"}), 400

    # ── Validate required fields ─────────────────────────────
    name  = (data.get("name")  or "").strip()
    email = (data.get("email") or "").strip()
    code  = (data.get("code")  or "").strip()

    errors = []
    if not name:
        errors.append("'name' is required")
    if not email:
        errors.append("'email' is required")
    elif not re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", email):
        errors.append("'email' is not a valid email address")
    if not code:
        errors.append("'code' is required")
    if errors:
        return jsonify({"error": "Validation failed", "details": errors}), 422

    # ── Build & save submission ───────────────────────────────
    slug     = slugify(name)
    filepath = unique_filepath(slug)
    filename = os.path.basename(filepath)

    submission = {
        "name":       name,
        "email":      email,
        "code":       code,
        "submitted_at": data.get("timestamp") or datetime.utcnow().isoformat() + "Z",
        "saved_as":   filename,
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(submission, f, indent=2, ensure_ascii=False)

    print(f"[+] Saved submission from '{name}' <{email}> → {filepath}")

    return jsonify({
        "message": f"Submission received and saved successfully.",
        "file":    filename,
        "name":    name,
        "email":   email,
    }), 201


@app.route("/submissions", methods=["GET"])
def list_submissions():
    """List all saved submissions (name, email, timestamp, filename)."""
    files = sorted(
        f for f in os.listdir(SUBMISSIONS_DIR) if f.endswith(".json")
    )
    results = []
    for fname in files:
        path = os.path.join(SUBMISSIONS_DIR, fname)
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            results.append({
                "file":         fname,
                "name":         data.get("name"),
                "email":        data.get("email"),
                "submitted_at": data.get("submitted_at"),
            })
        except Exception:
            results.append({"file": fname, "error": "Could not read file"})
    return jsonify({"count": len(results), "submissions": results}), 200


@app.route("/submissions/<filename>", methods=["GET"])
def get_submission(filename):
    """Retrieve the full content of a single submission by filename."""
    # Safety: strip path traversal attempts
    filename = os.path.basename(filename)
    if not filename.endswith(".json"):
        filename += ".json"

    path = os.path.join(SUBMISSIONS_DIR, filename)
    if not os.path.exists(path):
        return jsonify({"error": f"Submission '{filename}' not found"}), 404

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return jsonify(data), 200


@app.route("/health", methods=["GET"])
def health():
    count = len([f for f in os.listdir(SUBMISSIONS_DIR) if f.endswith(".json")])
    return jsonify({"status": "ok", "submissions_on_disk": count}), 200


if __name__ == "__main__":
    print("=" * 50)
    print("  WebPad Submission Server")
    print("  POST  /submit             — receive a submission")
    print("  GET   /submissions        — list all submissions")
    print("  GET   /submissions/<file> — get one submission")
    print("  GET   /health             — health check")
    print("=" * 50)
    app.run(debug=True, host="0.0.0.0", port=5000)
