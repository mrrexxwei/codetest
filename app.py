from flask import Flask, request, jsonify, abort
from flask_cors import CORS
import json
from datetime import datetime
import os
import re
import subprocess
import sys

app = Flask(__name__)
CORS(app)

SUBMISSIONS_FOLDER = os.path.join(os.path.dirname(__file__), 'assets', 'submissions', "mcsa")
JS_SUBMISSIONS_FOLDER = os.path.join(os.path.dirname(__file__), 'assets', 'submissions', 'webcode')
PY_SUBMISSIONS_FOLDER = os.path.join(os.path.dirname(__file__), 'assets', 'submissions', 'pycode')

@app.route('/submit-quiz', methods=['POST', 'GET'])
def submit_quiz():
    if request.method == 'POST':
        data = request.get_json(force=True)
    else:
        data = request.args.to_dict()
    name = data.get('name') or data.get('studentName', 'Unknown')
    email = data.get('email') or data.get('studentEmail', 'unknown@email.com')
    answer_summary = data.get('answers', '')
    score = data.get('score', 'N/A')

    print(f"\n{'='*60}")
    print(f"Student Name: {name}")
    print(f"Email: {email}")
    print(f"Submitted At: {data.get('submitted_at', 'N/A')}")
    print(f"{'='*60}\n")
    print(f"Email: {email}")
    print(f"Submitted At: {data.get('submitted_at', 'N/A')}")
    print(f"{'='*60}\n")

    if not os.path.exists(SUBMISSIONS_FOLDER):
        os.makedirs(SUBMISSIONS_FOLDER)

    filename = os.path.join(
        SUBMISSIONS_FOLDER,
        f"{name.replace(' ', '_')}_text_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )


    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

    print(f"✓ Saved to: {filename}\n")
    return jsonify({'status': 'success', 'message': 'Quiz submitted successfully'})


def _safe_submission_path(filename: str) -> str:
    # Allow forward slashes for nested paths like "assets/submissions/pycode/2026-04-03/file.json"
    safe_name = re.sub(r'[^\w\-./ ]', '_', filename)
    path = os.path.abspath(os.path.join(os.path.dirname(__file__), safe_name))
    # Check if path is within allowed directories (submissions or assets/submissions)
    base_submissions = os.path.abspath(os.path.join(os.path.dirname(__file__), 'submissions'))
    base_assets_submissions = os.path.abspath(os.path.join(os.path.dirname(__file__), 'assets/submissions'))
    
    is_valid = (path.startswith(base_submissions + os.sep) or path == base_submissions or
                path.startswith(base_assets_submissions + os.sep) or path == base_assets_submissions)
    
    if not is_valid:
        abort(400, description='Invalid submission file path')
    return path


@app.route('/submit-code', methods=['POST', 'GET'])
def submit_code():
    if request.method == 'POST':
        data = request.get_json(force=True)
    else:
        data = request.args.to_dict()
    name = data.get('name') or data.get('studentName', 'Unknown')
    email = data.get('email') or data.get('studentEmail', 'unknown@email.com')
    answer_summary = data.get('answers', '')
    score = data.get('score', 'N/A')

    print(f"\n{'='*60}")
    print(f"Student Name: {name}")
    print(f"Email: {email}")
    print(f"Submitted At: {data.get('submitted_at', 'N/A')}")
    print(f"{'='*60}\n")

    # Determine submission type: Python code or Web code
    is_python_submission = 'tasks' in data  # pytask.html sends tasks array
    is_web_submission = 'code' in data and 'tasks' not in data  # webcode.html sends merged code

    # Determine the submission folder
    folder_path = data.get('folder')
    
    if folder_path:
        # Use the folder specified in the payload (e.g., assets/submissions/pycode/2026-04-03)
        save_folder = os.path.join(os.path.dirname(__file__), folder_path)
        submission_type = 'python'
    elif is_python_submission:
        # Python submission without explicit folder
        save_folder = SUBMISSIONS_FOLDER
        submission_type = 'python'
    elif is_web_submission:
        # Web submission (HTML/CSS/JS)
        today = datetime.now().strftime('%Y-%m-%d')
        web_submissions_folder = os.path.join(os.path.dirname(__file__), f'assets/submissions/webcode/{today}')
        save_folder = web_submissions_folder
        submission_type = 'web'
    else:
        # Unknown type, use default folder
        save_folder = SUBMISSIONS_FOLDER
        submission_type = 'unknown'

    # Create folder if it doesn't exist
    if not os.path.exists(save_folder):
        os.makedirs(save_folder)

    # Generate filename based on submission type
    if is_python_submission:
        file_prefix = 'pycode'
    elif is_web_submission:
        file_prefix = 'webcode'
    else:
        file_prefix = 'submission'
    
    filename = os.path.join(
        save_folder,
        f"{name.replace(' ', '_')}_{file_prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

    print(f"✓ Saved {submission_type} submission to: {filename}\n")
    return jsonify({'status': 'success', 'message': 'Code submitted successfully', 'type': submission_type})


def _safe_submission_path(filename: str) -> str:
    safe_name = re.sub(r'[^\w\-.]', '_', filename)
    path = os.path.abspath(os.path.join(SUBMISSIONS_FOLDER, safe_name))
    if not path.startswith(os.path.abspath(SUBMISSIONS_FOLDER) + os.sep):
        abort(400, description='Invalid submission file name')
    return path


@app.route('/submissions/<path:filename>', methods=['POST', 'GET'])
def get_submission(filename):
    path = _safe_submission_path(filename)
    if not os.path.exists(path):
        abort(404, description='Submission not found')
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return jsonify(data)


# ======= check MCSA submission ======= 
@app.route('/checkmc', methods=['POST', 'GET'])
def list_submissions():
    if not os.path.exists(SUBMISSIONS_FOLDER):
        return jsonify([])
    files = [f for f in os.listdir(SUBMISSIONS_FOLDER) if f.lower().endswith('.json')]
    submissions = []
    for fn in sorted(files, reverse=True):
        try:
            with open(os.path.join(SUBMISSIONS_FOLDER, fn), 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception:
            continue
        submissions.append({
            'filename': fn,
            'types': 'code' if 'code' in fn else 'quiz',
            'name': data.get('name') or data.get('studentName'),
            'email': data.get('email') or data.get('studentEmail'),
            'score': data.get('score'),
            'submitted_at': data.get('submitted_at'),
        })
    return jsonify(submissions)

# ======= check Web Code submission ======= 
# @app.route("/checkcode", methods=["GET"])
# def check_code():
#     """List all saved submissions (name, email, timestamp, filename)."""
#     files = sorted(
#         f for f in os.listdir(SUBMISSIONS_FOLDER) if f.endswith(".json")
#     )
#     results = []
#     for fname in files:
#         path = os.path.join(SUBMISSIONS_FOLDER, fname)
#         try:
#             with open(path, "r", encoding="utf-8") as f:
#                 data = json.load(f)
#                 results.append({
#                 "file":         fname,
#                 "types":         "code" if "code" in fname else "quiz",
#                 "name":         data.get("name"),
#                 "email":        data.get("email"),
#                 "submitted_at": data.get("submitted_at"),
#             })
#         except Exception:
#             results.append({"file": fname, "error": "Could not read file"})
#     return jsonify({"count": len(results), "submissions": results}), 200


# ======= check HTML/CSS/JS code submission ======= 
@app.route("/readjs", methods=["GET"])
def check_code():
    """List all saved submissions (name, email, timestamp, filename)."""

    print(f"Checking submissions in: {JS_SUBMISSIONS_FOLDER}")

    files = sorted(
        f for f in os.listdir(JS_SUBMISSIONS_FOLDER) if f.endswith(".json")
    )
    results = []
    for fname in files:
        path = os.path.join(JS_SUBMISSIONS_FOLDER, fname)
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                results.append({
                "file":         fname,
                "types":         "code" if "code" in fname else "quiz",
                "name":         data.get("name"),
                "email":        data.get("email"),
                "submitted_at": data.get("submitted_at"),
            })
        except Exception:
            results.append({"file": fname, "error": "Could not read file"})
    return jsonify({"count": len(results), "submissions": results}), 200


@app.route('/health', methods=['POST', 'GET'])
def health():
    return jsonify({'status': 'Server is running'})


# ======= List Python submission folders =======
@app.route('/pycode-folders', methods=['GET'])
def list_pycode_folders():
    """List all date folders in assets/submissions/pycode."""
    pycode_path = os.path.join(os.path.dirname(__file__), 'assets/submissions/pycode')
    
    if not os.path.exists(pycode_path):
        return jsonify({'folders': []})
    
    try:
        folders = [
            f for f in os.listdir(pycode_path)
            if os.path.isdir(os.path.join(pycode_path, f))
        ]
        # Sort in reverse order (newest first)
        folders.sort(reverse=True)
        return jsonify({'folders': folders})
    except Exception as e:
        return jsonify({'folders': [], 'error': str(e)})


# ======= List submissions from a specific pycode folder =======
@app.route('/pycode-submissions/<folder>', methods=['GET'])
def list_pycode_submissions(folder):
    """List all JSON files in a specific pycode folder."""
    pycode_path = os.path.join(os.path.dirname(__file__), 'assets/submissions/pycode', folder)
    
    # Security check: prevent directory traversal
    if not os.path.abspath(pycode_path).startswith(os.path.abspath(os.path.join(os.path.dirname(__file__), 'assets/submissions/pycode'))):
        return jsonify({'error': 'Invalid folder'}), 400
    
    # print(f"Checking folder: {pycode_path}")

    if not os.path.exists(pycode_path):
        print(f"Folder not found: {pycode_path}")
        return jsonify({'error': 'Folder not found'}), 404
    
    # print(f"Found folder: {pycode_path}, listing files...")
    try:
        files = sorted(
            [f for f in os.listdir(pycode_path) if f.endswith('.json')],
            reverse=True
        )
        
        results = []
        for fname in files:
            filepath = os.path.join(pycode_path, fname)
            # print(f"Reading file: {filepath}")
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    results.append({
                        'file': fname,
                        'name': data.get('name'),
                        'email': data.get('email'),
                        'submitted_at': data.get('timestamp'),
                    })
                # print(f"found submission: {fname}")
            except Exception:
                results.append({'file': fname, 'error': 'Could not read file'})
        
        return jsonify({'folder': folder, 'count': len(results), 'submissions': results})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ======= Get a specific Python submission file =======
@app.route('/python-submissions/<path:filepath>', methods=['GET'])
def get_python_submission(filepath):
    """Fetch a specific Python submission file from pycode folder."""
    # Security check: filepath should be like "assets/submissions/pycode/2026-04-03/filename.json"
    full_path = os.path.join(os.path.dirname(__file__), filepath)
    base_pycode = os.path.abspath(os.path.join(os.path.dirname(__file__), 'assets/submissions/pycode'))
    
    if not os.path.abspath(full_path).startswith(base_pycode):
        return jsonify({'error': 'Invalid file path'}), 400
    
    if not os.path.exists(full_path):
        return jsonify({'error': 'File not found'}), 404
    
    if not full_path.endswith('.json'):
        return jsonify({'error': 'Invalid file type'}), 400
    
    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return jsonify(data)
    except json.JSONDecodeError:
        return jsonify({'error': 'Invalid JSON file'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ======= List web code submission folders Step 01 =======
@app.route('/webcode-folders', methods=['GET'])
def list_webcode_folders():
    """List all date folders in assets/submissions/webcode."""
    webcode_path = os.path.join(os.path.dirname(__file__), 'assets/submissions/webcode')
    
    if not os.path.exists(webcode_path):
        return jsonify({'folders': []})
    
    try:
        folders = [
            f for f in os.listdir(webcode_path)
            if os.path.isdir(os.path.join(webcode_path, f))
        ]
        # Sort in reverse order (newest first)
        folders.sort(reverse=True)
        return jsonify({'folders': folders})
    except Exception as e:
        return jsonify({'folders': [], 'error': str(e)})


# ======= List submissions from a specific webcode folder Step 02 =======
@app.route('/webcode-submissions/<folder>', methods=['GET'])
def list_webcode_submissions(folder):
    """List all JSON files in a specific webcode folder."""
    webcode_path = os.path.join(os.path.dirname(__file__), 'assets/submissions/webcode', folder)
    
    # Security check: prevent directory traversal
    if not os.path.abspath(webcode_path).startswith(os.path.abspath(os.path.join(os.path.dirname(__file__), 'assets/submissions/webcode'))):
        return jsonify({'error': 'Invalid folder'}), 400
    
    if not os.path.exists(webcode_path):
        return jsonify({'error': 'Folder not found'}), 404
    print(f"Found folder: {webcode_path}, listing files...")
    try:
        files = sorted(
            [f for f in os.listdir(webcode_path) if f.endswith('.json')],
            reverse=True
        )
        
        results = []
        for fname in files:
            filepath = os.path.join(webcode_path, fname)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    results.append({
                        'file': fname,
                        'name': data.get('name'),
                        'email': data.get('email'),
                        'submitted_at': data.get('timestamp'),
                    })
            except Exception:
                results.append({'file': fname, 'error': 'Could not read file'})
        
        return jsonify({'folder': folder, 'count': len(results), 'submissions': results})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ======= Get a specific web submission file Step 03 =======
@app.route('/web-subdetail/<path:filepath>', methods=['GET'])
def get_web_submission(filepath):
    """Fetch a specific web submission file from webcode folder."""
    # Security check: filepath should be like "assets/submissions/webcode/2026-04-03/filename.json"
    full_path = os.path.join(os.path.dirname(__file__), filepath)
    base_webcode = os.path.abspath(os.path.join(os.path.dirname(__file__), 'assets/submissions/webcode'))
    
    if not os.path.abspath(full_path).startswith(base_webcode):
        return jsonify({'error': 'Invalid file path'}), 400
    
    if not os.path.exists(full_path):
        return jsonify({'error': 'File not found'}), 404
    
    if not full_path.endswith('.json'):
        return jsonify({'error': 'Invalid file type'}), 400
    
    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return jsonify(data)
    except json.JSONDecodeError:
        return jsonify({'error': 'Invalid JSON file'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/execute-python', methods=['POST'])
def execute_python():
    """Execute Python code and return output."""
    try:
        data = request.get_json()
        code = data.get('code', '')
        
        if not code or not code.strip():
            return jsonify({'output': '', 'error': 'No code provided', 'success': False})
        
        # Run Python code in a subprocess with timeout
        try:
            result = subprocess.run(
                [sys.executable, '-c', code],
                capture_output=True,
                text=True,
                timeout=10  # 10 second timeout
            )
            
            output = result.stdout
            error = result.stderr
            
            return jsonify({
                'output': output,
                'error': error,
                'success': result.returncode == 0
            })
        except subprocess.TimeoutExpired:
            return jsonify({
                'output': '',
                'error': 'Execution timeout (>5 seconds)',
                'success': False
            })
    except Exception as e:
        return jsonify({
            'output': '',
            'error': str(e),
            'success': False
        })


if __name__ == '__main__':
    print("Starting Flask server on http://localhost:5000")
    print("Make sure your quiz HTML is pointing to http://localhost:5000/submit-quiz")
    app.run(host='0.0.0.0', port=5000)
