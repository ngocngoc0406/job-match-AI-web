import re
import os

with open('web/app.py', 'r', encoding='utf-8') as f:
    code = f.read()

# 1. Imports
code = code.replace('from flask import Flask, render_template, request, jsonify, send_file',
                    'from flask import Flask, render_template, request, jsonify, send_file, session\nfrom werkzeug.security import generate_password_hash, check_password_hash\nimport uuid')

# 2. Add secret key and user functions
setup_code = '''
app.secret_key = os.environ.get("SECRET_KEY", os.urandom(24))

USERS_FILE = os.path.join(os.path.dirname(__file__), 'data', 'users.json')

def load_users():
    if not os.path.exists(USERS_FILE):
        os.makedirs(os.path.dirname(USERS_FILE), exist_ok=True)
        return {}
    with open(USERS_FILE, 'r', encoding='utf-8') as f:
        import json
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def save_users(users):
    os.makedirs(os.path.dirname(USERS_FILE), exist_ok=True)
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        import json
        json.dump(users, f, indent=4)

user_sessions_store = {}

def get_user_state():
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    sid = session['session_id']
    if sid not in user_sessions_store:
        user_sessions_store[sid] = {
            'cv_text': None, 'USER_ID': None, 'scores': None, 'user_prob': None,
            'user_city': None, 'user_detail': None, 'user_role_can': None,
            'user_exp_bucket': None, 'user_raw2can_best': None, 'user_raw2can_map': None,
            'current_G': None, 'cv_vec': None, 'cv_filename': None
        }
    return user_sessions_store[sid]

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    name = data.get('name', 'User')
    users = load_users()
    if email in users: return jsonify({'error': 'Email already registered'}), 400
    users[email] = {'name': name, 'password_hash': generate_password_hash(password)}
    save_users(users)
    session['user_email'] = email
    return jsonify({'success': True})

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    users = load_users()
    user = users.get(email)
    if not user or not check_password_hash(user['password_hash'], password):
        return jsonify({'error': 'Invalid credentials'}), 401
    session['user_email'] = email
    return jsonify({'success': True})

@app.route('/api/logout', methods=['POST'])
def logout():
    session.pop('user_email', None)
    return jsonify({'success': True})

@app.route('/api/auth-status')
def auth_status():
    email = session.get('user_email')
    if not email: return jsonify({'logged_in': False})
    user = load_users().get(email, {})
    return jsonify({'logged_in': True, 'user': {'email': email, 'name': user.get('name', 'User')}})
'''
if "app.secret_key" not in code:
    code = code.replace("app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER", "app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER\n" + setup_code)

# 3. Inject user_state = get_user_state() into functions where state is used for user variables
functions_to_modify = [
    'def upload_page():',
    'def upload_files():',
    'def results():',
    'def cv_full():',
    'def user_skills():',
    'def statistics():',
    'def graph_data():',
    'def interview_chat():',
    'def interview_summary():',
    'def user_profile():',
    'def cv_data():'
]
for fn in functions_to_modify:
    code = code.replace(fn, fn + '\n    user_state = get_user_state()')

# 4. Modify job_detail which already has try: handle properly
code = code.replace('def job_detail(job_id):', "def job_detail(job_id):\n    user_state = get_user_state()")

# 5. Global replacement: Replace state['cv_text'], state.get('cv_text') etc. with user_state
user_keys = [
    'cv_text', 'cv_filename', 'USER_ID', 'scores', 'user_prob', 'user_city',
    'user_detail', 'user_role_can', 'user_exp_bucket', 'user_raw2can_best',
    'user_raw2can_map', 'current_G', 'cv_vec'
]
for key in user_keys:
    # Handle state['key']
    code = re.sub(rf"state\s*\[\s*['\"]{key}['\"]\s*\]", f"user_state['{key}']", code)
    # Handle state.get('key') or state.get('key', default)
    code = re.sub(rf"state\.get\s*\(\s*['\"]{key}['\"]", f"user_state.get('{key}'", code)

# Note: keep state['job_nodes'], state['df'] etc. pointing to global `state`


# Rewrite back
with open('web/app.py', 'w', encoding='utf-8') as f:
    f.write(code)

print("Refactored successfully")
