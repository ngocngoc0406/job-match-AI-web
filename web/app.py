# -*- coding: utf-8 -*-
"""Flask web application for NCKH job matching system"""

from flask import Flask, render_template, request, jsonify, send_file
import os
import re
import json
from time import perf_counter
from werkzeug.utils import secure_filename
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize

from config import (
    TOPK_USER_JOB, CORE_SKILLS_CANON, SIM_THRESHOLD, 
    CANDIDATES_TOP, TOPK_SIMILAR, MIN_KEEP_PROB
)
from utils.data_loader import load_excel_file, load_pdf_file, extract_all_text_from_pdf
from utils.text_processing import (
    norm_text, infer_role_canonical, parse_year_range, exp_bucket, 
    parse_location_city_detail, short_label
)
from scoring.skill_variants import extract_skills_probabilistic
from visualization.graph_visualization import clean_focus_layout
from kg.graph_init import init_rdf_graph
from kg.job_builder import build_job_nodes
from kg.user_builder import build_user_node, build_strict_user_job_graph
from scoring.user_job_score import compute_user_job_scores
from scoring.xai import explain_user_job
from kg.similarity import build_job_job_similar_edges
import networkx as nx
from networkx.readwrite import json_graph

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max file size
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Global variables to store state
state = {
    'df': None,
    'cv_text': None,
    'USER_ID': None,
    'job_nodes': None,
    'job_info': None,
    'scores': None,
    'user_prob': None,
    'user_city': None,
    'user_detail': None,
    'user_role_can': None,
    'user_exp_bucket': None,
    'user_raw2can_best': None,
    'user_raw2can_map': None,
    'G': None,          # Base job graph
    'current_G': None,  # Working graph (User + Jobs)
    'tfidf': None,
    'X': None,
    'IDX': None,
    'cv_vec': None,
    'valid_job_nodes': None,
    'is_ready': False,  # Tracking initialization
}

DASHBOARD_DATA_FILE = os.path.join(os.path.dirname(__file__), 'data', 'dashboard_data.json')

def load_dashboard_data():
    if not os.path.exists(DASHBOARD_DATA_FILE):
        return {
            "kanban": {"saved": [], "applied": [], "interview": [], "offer": []},
            "activity": [],
            "stats": {"scans": 0, "matches": 0}
        }
    with open(DASHBOARD_DATA_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_dashboard_data(data):
    os.makedirs(os.path.dirname(DASHBOARD_DATA_FILE), exist_ok=True)
    with open(DASHBOARD_DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def log_activity(atype, title, subtitle):
    data = load_dashboard_data()
    icons = {
        'scan': 'bi-file-earmark-pdf',
        'move': 'bi-arrow-right-circle',
        'interview': 'bi-calendar-check',
        'builder': 'bi-pencil-square',
        'match': 'bi-lightning-charge'
    }
    colors = {
        'scan': 'info',
        'move': 'primary',
        'interview': 'warning',
        'builder': 'success',
        'match': 'danger'
    }
    
    from datetime import datetime
    new_act = {
        "type": atype,
        "title": title,
        "subtitle": subtitle,
        "time": datetime.now().strftime("%I:%M %p, %b %d"),
        "icon": icons.get(atype, 'bi-info-circle'),
        "color": colors.get(atype, 'primary')
    }
    data['activity'].insert(0, new_act)
    data['activity'] = data['activity'][:15] # Keep last 15
    save_dashboard_data(data)

@app.route('/')
def index():
    """Home page"""
    return render_template('index.html')

@app.route('/upload_page')
def upload_page():
    return render_template('pages/upload.html', cv_filename=state.get('cv_filename'))

@app.route('/dashboard')
def dashboard():
    return render_template('pages/dashboard.html')

@app.route('/search')
def search_page():
    return render_template('pages/search.html')

@app.route('/cv-builder')
def cv_builder():
    return render_template('pages/cv_builder.html')

@app.route('/results-page')
def results_page():
    return render_template('pages/results.html')

@app.route('/graph-page')
def graph_page():
    return render_template('pages/graph.html')

@app.route('/skills-page')
def skills_page():
    return render_template('pages/skills.html')

@app.route('/stats-page')
def stats_page():
    return render_template('pages/stats.html')

@app.route('/interview-page')
def interview_page():
    return render_template('pages/interview.html')

@app.route('/salary-page')
def salary_page():
    return render_template('pages/salary.html')

# --- Dashboard API ---

@app.route('/api/dashboard')
def get_dashboard_data():
    data = load_dashboard_data()
    # Update stats based on session if needed, or just return persistent ones
    return jsonify(data)

@app.route('/api/kanban/update', methods=['POST'])
def update_kanban_state():
    new_kanban = request.json
    data = load_dashboard_data()
    data['kanban'] = new_kanban
    save_dashboard_data(data)
    return jsonify({'success': True})

@app.route('/api/kanban/add', methods=['POST'])
def add_kanban_item():
    item = request.json # {title, company, loc, status}
    data = load_dashboard_data()
    status = item.get('status', 'saved')
    
    from datetime import datetime
    new_card = {
        "id": "kb_" + datetime.now().strftime("%Y%m%d%H%M%S"),
        "title": item.get('title'),
        "company": item.get('company'),
        "loc": item.get('loc', 'Unknown'),
        "date": datetime.now().strftime("%b %d, %Y")
    }
    
    if status in data['kanban']:
        data['kanban'][status].append(new_card)
        log_activity('move', 'New Application', f"Added {new_card['title']} at {new_card['company']}")
        save_dashboard_data(data)
        return jsonify({'success': True, 'item': new_card})
    return jsonify({'error': 'Invalid status'}), 400

@app.route('/user-skills')
def get_user_skills():
    if state.get('user_prob') is None:
        return jsonify([])
    # Return sorted skills
    sorted_skills = sorted(
        [{'name': k, 'probability': v} for k, v in state['user_prob'].items()],
        key=lambda x: x['probability'],
        reverse=True
    )
    return jsonify(sorted_skills)

@app.route('/upload', methods=['POST'])
def upload_files():
    """Handle file uploads"""
    try:
        if not state.get('is_ready'):
            return jsonify({'error': 'System is still initializing. Please wait a few moments...'}), 503
            
        pdf_file = request.files.get('pdf_file')

        # Check if PDF file is provided
        if not pdf_file:
            return jsonify({'error': 'PDF file required'}), 400

        # Always use default Excel file
        excel_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'db_job_tuan.xlsx')
        if not os.path.exists(excel_path):
            return jsonify({'error': 'Default job database (db_job_tuan.xlsx) not found'}), 400

        # Save PDF temporarily
        pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(pdf_file.filename))
        pdf_file.save(pdf_path)

        try:
            # 1. Load CV text
            cv_text = extract_all_text_from_pdf(pdf_path, verbose=False)
            state['cv_text'] = cv_text
            state['cv_filename'] = pdf_file.filename

            # 2. Get pre-computed data from state
            job_info = state['job_info']
            job_nodes = state['job_nodes']
            valid_job_nodes = state['valid_job_nodes']
            tfidf = state['tfidf']
            X = state['X']
            IDX = state['IDX']
            
            # 3. Create a clean working graph
            G = state['G'].copy()
            state['current_G'] = G

            # 4. Build user node and extract skills
            USER_ID, user_prob, user_city, user_detail, user_raw2can_map, user_raw2can_best = \
                build_user_node(G, cv_text)

            state['USER_ID'] = USER_ID
            state['user_prob'] = user_prob
            state['user_city'] = user_city
            state['user_detail'] = user_detail
            state['user_raw2can_map'] = user_raw2can_map
            state['user_raw2can_best'] = user_raw2can_best
            state['user_role_can'] = infer_role_canonical(cv_text)
            user_exp_min, user_exp_max, _ = parse_year_range(cv_text)
            state['user_exp_bucket'] = exp_bucket(user_exp_min, user_exp_max) if user_exp_min is not None else "Exp_Unknown"

            # 5. Transform CV text to TF-IDF
            cv_vec = normalize(tfidf.transform([norm_text(cv_text)]))
            state['cv_vec'] = cv_vec

            # 6. Compute user-job match scores
            scores = compute_user_job_scores(
                job_nodes, job_info, user_prob, user_city, user_detail,
                IDX, X, cv_vec, tfidf, state['user_role_can'], 
                state['user_exp_bucket'], user_raw2can_best, user_raw2can_map
            )
            state['scores'] = scores

            # 7. Add MATCHES_JOB edges
            for job_node, score, explain in scores:
                G.add_edge(USER_ID, job_node, rel="MATCHES_JOB", score=round(score, 3))

            return jsonify({
                'success': True,
                'jobs_count': len(job_nodes),
                'skills_detected': len(user_prob),
                'user_city': user_city,
                'user_role': state['user_role_can'],
                'cv_filename': pdf_file.filename
            })
        finally:
            # Log activity and update stats
            log_activity('scan', 'CV Analyzed', f"Extracted {len(user_prob)} skills from {pdf_file.filename}")
            db_data = load_dashboard_data()
            db_data['stats']['scans'] += 1
            save_dashboard_data(db_data)
            
            if os.path.exists(pdf_path):
                os.remove(pdf_path)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/results')
def results():
    """Display matching results"""
    if state.get('scores') is None:
        return jsonify([])

    results_data = []
    for rank, (j, sc, ex) in enumerate(state['scores'][:TOPK_USER_JOB], start=1):
        job_title = short_label(state['job_info'][j]['title'], 90)
        results_data.append({
            'rank': rank,
            'score': sc,
            'title': job_title,
            'full_title': state['job_info'][j]['title'],
            'city': state['job_info'][j]['city'],
            'company': state['job_info'][j].get('company', 'N/A'),
            'url': state['job_info'][j]['url'],
        })

    return jsonify(results_data)

@app.route('/api/cv-full')
def cv_full():
    """Return full extracted CV text and structured info"""
    if not state.get('is_ready'):
        return jsonify({'active': False, 'initializing': True})

    if state.get('cv_text') is None:
        return jsonify({'active': False})
    
    cv_text = state['cv_text']
    
    # Extract structured info
    email_match = re.search(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}', cv_text)
    phone_match = re.search(r'(?:\+84|0)\s*\d[\d\s.\-]{7,12}', cv_text)
    
    skills = list(state.get('user_prob', {}).keys())
    
    return jsonify({
        'active': True,
        'cv_text': cv_text,
        'char_count': len(cv_text),
        'line_count': len(cv_text.split('\n')),
        'role': state.get('user_role_can', 'Unknown'),
        'city': state.get('user_city', 'Unknown'),
        'email': email_match.group(0) if email_match else '',
        'phone': re.sub(r'\s+', '', phone_match.group(0)) if phone_match else '',
        'skills': skills[:20],
        'skills_count': len(skills),
        'filename': state.get('cv_filename', ''),
    })


@app.route('/job/<job_id>')
def job_detail(job_id):
    """Get detailed job information"""
    try:
        # Find job by index
        if int(job_id) >= len(state['scores']):
            return jsonify({'error': 'Job not found'}), 404

        j, sc, ex = state['scores'][int(job_id)]
        job_info = state['job_info'][j]
        job_prob = job_info["prob_skills"]

        if state['user_raw2can_best']:
            user_prob_max_raw = {
                canon: float(p)
                for canon, (_, p) in state['user_raw2can_best'].items()
                if isinstance(p, (int, float))
            }
        else:
            user_prob_max_raw = state['user_prob']

        xai = explain_user_job(user_prob_max_raw, job_prob, 
                              user_raw2can=state['user_raw2can_map'], 
                              job_raw2can=job_info.get('raw2can'))

        detail = {
            'title': job_info['title'],
            'company': job_info.get('company', 'N/A'),
            'city': job_info['city'],
            'url': job_info['url'],
            'score': sc,
            'components': ex['components'],
            'skill_coverage': f"{xai['components']['skill_coverage']*100:.1f}%",
            'matched_skills': xai['evidence']['matched_skills'][:10],
            'missing_skills': xai['evidence']['missing_skills'][:10],
        }

        return jsonify(detail)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/user-skills')
def user_skills():
    """Get detected user skills"""
    skills = []
    for k, v in sorted(state['user_prob'].items(), key=lambda x: x[1], reverse=True):
        core_tag = "CORE" if k in CORE_SKILLS_CANON else ""
        skills.append({
            'name': k,
            'probability': float(v),  # Keep full precision
            'is_core': k in CORE_SKILLS_CANON,
            'tag': core_tag
        })

    return jsonify(skills)

@app.route('/statistics')
def statistics():
    """Get dataset statistics"""
    job_nodes = state['job_nodes']
    job_info = state['job_info']

    # Calculate stats
    Cj_sizes = [len(job_info[j]["prob_skills"]) for j in job_nodes if j in job_info]
    Cj_sizes = np.array(Cj_sizes)

    stats = {
        'total_jobs': len(job_nodes),
        'user_skills': len(state['user_prob']),
        'avg_job_skills': round(Cj_sizes.mean(), 3),
        'median_job_skills': round(np.median(Cj_sizes), 3),
        'min_job_skills': int(Cj_sizes.min()),
        'max_job_skills': int(Cj_sizes.max()),
    }

    return jsonify(stats)

# @app.route('/graph')
# def graph_data():
#     """Get graph visualization data"""
#     # Ensure the graph is available and the CV has been processed
#     if state['G'] is None or state['cv_text'] is None:
#         return jsonify({'error': 'No graph available. Please upload a CV first.'}), 400

#     try:
#         # Use H from state
#         H = state['G']
        
#         # Limit graph size for visualization (top nodes)
#         if len(H.nodes()) > 200:
#             # Get user node and top job nodes
#             user_nodes = [n for n in H.nodes() if H.nodes[n].get('ntype') == 'User']
#             job_nodes = [n for n in H.nodes() if H.nodes[n].get('ntype') == 'JobPosting']
#             skill_nodes = [n for n in H.nodes() if H.nodes[n].get('ntype') in ['Skill', 'SkillRaw']]
            
#             # Take sample
#             selected_jobs = job_nodes[:30]  # Top 30 jobs
#             selected_skills = skill_nodes[:50]  # Top 50 skills
#             selected_nodes = user_nodes + selected_jobs + selected_skills
            
#             # Create subgraph
#             H_sub = H.subgraph(selected_nodes).copy()
#         else:
#             H_sub = H
        
#         # Convert to JSON format for visualization
#         data = json_graph.node_link_data(H_sub)
        
#         # Add additional info
#         graph_info = {
#             'nodes': len(H_sub.nodes()),
#             'edges': len(H_sub.edges()),
#             'total_nodes': len(H.nodes()),
#             'total_edges': len(H.edges()),
#             'data': data
#         }
        
#         return jsonify(graph_info)
#     except Exception as e:
#         return jsonify({'error': str(e)}), 500
@app.route('/graph')
def graph_data():
    """Get focused knowledge graph data for visualization.
    Requires CV upload first to populate user node + MATCHES_JOB edges.
    Returns nodes/links with pre-computed positions.
    """
    # More specific state checks
    if state.get('cv_text') is None:
        return jsonify({'error': 'No CV uploaded yet. Please upload your CV first to generate the knowledge graph.'}), 400
    if state.get('USER_ID') is None:
        return jsonify({'error': 'User node not created. CV processing incomplete.'}), 400
    if state.get('current_G') is None:
        return jsonify({'error': 'Graph state missing. Try re-uploading your CV.'}), 400

    try:
        import logging
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)
        
        G = state['current_G']
        USER_ID = state['USER_ID']  # Safe now due to prior checks

        logger.info(f"Generating graph for USER_ID={USER_ID}, G.nodes={len(G.nodes())}")
        
        # Center on user node
        center_node = USER_ID

        # --- build focus subgraph (logic chuẩn của bạn)
        H = build_strict_user_job_graph(
            G,
            user_node=USER_ID,
            topk=TOPK_USER_JOB
        )

        # --- layout
        from visualization.graph_visualization import clean_focus_layout
        pos = clean_focus_layout(H, center_node)

        # --- serialize nodes
        nodes = []
        for n in H.nodes():
            x, y = pos.get(n, (0.0, 0.0))
            nodes.append({
                "id": n,
                "label": H.nodes[n].get("label", ""),
                "ntype": H.nodes[n].get("ntype", "Other"),
                "x": float(x),
                "y": float(y)
            })

        # --- serialize edges
        links = []
        for u, v, d in H.edges(data=True):
            links.append({
                "source": u,
                "target": v,
                "rel": d.get("rel"),
                "score": d.get("score"),
                "prob": d.get("prob")
            })

        return jsonify({
            "nodes": nodes,
            "links": links,
            "nodes_count": len(nodes),
            "links_count": len(links),
            "total_nodes": len(G.nodes()),
            "total_edges": len(G.edges())
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

def process_graph(H, center_node, max_nodes=200):
    """Process the graph and generate layout positions"""
    try:
        # Validate center_node
        if center_node not in H:
            raise ValueError("Invalid center node")

        # Focus on the neighborhood of the center node
        neighborhood = set(H.neighbors(center_node))
        neighborhood.add(center_node)

        # Limit the number of nodes for visualization
        if len(neighborhood) > max_nodes:
            neighborhood = set(list(neighborhood)[:max_nodes])

        # Create a subgraph for the neighborhood
        H_sub = H.subgraph(neighborhood).copy()

        # Generate layout
        pos = nx.spring_layout(H_sub, k=0.15, iterations=20)

        return pos
    except Exception as e:
        raise RuntimeError(f"Error processing graph: {e}")

def _analyze_response(user_msg, cv_skills):
    """
    Smart NLP analysis of user's interview response.
    Returns dict with: mentioned_skills, mentioned_tools, sentiment_keywords,
    word_count, has_example, has_numbers, depth_score
    """
    import re
    msg_lower = user_msg.lower()
    words = msg_lower.split()
    word_count = len(words)

    # 1. Detect skills mentioned (match against CV skill list + common tech)
    common_tech = [
        'python', 'java', 'javascript', 'typescript', 'react', 'angular', 'vue',
        'node', 'django', 'flask', 'fastapi', 'spring', 'docker', 'kubernetes',
        'aws', 'azure', 'gcp', 'sql', 'nosql', 'mongodb', 'postgresql', 'mysql',
        'redis', 'kafka', 'tensorflow', 'pytorch', 'scikit-learn', 'pandas',
        'numpy', 'spark', 'hadoop', 'airflow', 'git', 'ci/cd', 'jenkins',
        'linux', 'api', 'rest', 'graphql', 'microservices', 'agile', 'scrum',
        'machine learning', 'deep learning', 'nlp', 'computer vision', 'ai',
        'data science', 'data engineering', 'devops', 'cloud', 'html', 'css',
        'c++', 'c#', 'go', 'rust', 'kotlin', 'swift', 'r', 'matlab',
        'tableau', 'power bi', 'excel', 'figma', 'jira', 'confluence'
    ]
    all_skills = set(s.lower() for s in cv_skills) | set(common_tech)
    
    mentioned_skills = []
    for skill in all_skills:
        if skill in msg_lower:
            mentioned_skills.append(skill)
    
    # 2. Detect action/result keywords (STAR method indicators)
    action_words = ['built', 'created', 'developed', 'designed', 'implemented',
                    'led', 'managed', 'optimized', 'improved', 'reduced', 'increased',
                    'automated', 'deployed', 'launched', 'migrated', 'refactored',
                    'solved', 'fixed', 'analyzed', 'trained', 'mentored',
                    'xây dựng', 'phát triển', 'thiết kế', 'tối ưu', 'cải thiện',
                    'triển khai', 'quản lý', 'dẫn dắt', 'giải quyết', 'tạo']
    found_actions = [w for w in action_words if w in msg_lower]
    
    # 3. Detect if they gave a concrete example
    example_markers = ['for example', 'for instance', 'such as', 'specifically',
                       'in one project', 'at my', 'when i', 'i once', 'last year',
                       'ví dụ', 'cụ thể', 'trong dự án', 'tại công ty', 'khi tôi']
    has_example = any(m in msg_lower for m in example_markers)
    
    # 4. Detect numbers/metrics (shows quantitative thinking)
    has_numbers = bool(re.search(r'\d+', user_msg))
    number_context = re.findall(r'(\d+\s*(?:%|percent|users|customers|months|years|team|people|projects|hours|days|times|x|gb|tb|ms|seconds|năm|tháng|người|dự án))', msg_lower)
    
    # 5. Detect STAR Method components
    star_analysis = {
        'S': bool(re.search(r'\b(at|in|when|during|tại|khi|trong khi|ở)\b.*\b(project|company|company|team|time|dự án|công ty|đội)\b', msg_lower)),
        'T': bool(re.search(r'\b(task|goal|objective|aim|responsibility|nhiệm vụ|mục tiêu|trách nhiệm)\b', msg_lower)),
        'A': len(found_actions) >= 2,
        'R': bool(re.search(r'\b(result|outcome|achieved|success|delivered|kết quả|đạt được|thành công)\b', msg_lower)) or has_numbers
    }
    
    # 6. Sentiment / confidence keywords
    positive_words = ['passionate', 'love', 'enjoy', 'excited', 'proud', 'achieved',
                      'successful', 'thích', 'đam mê', 'tự hào', 'thành công']
    negative_words = ['struggle', 'difficult', 'challenge', 'hard', 'failed', 'issue', 'problem',
                      'khó', 'thử thách', 'thất bại', 'vấn đề', 'trở ngại']
    has_positive = any(w in msg_lower for w in positive_words)
    has_challenge = any(w in msg_lower for w in negative_words)
    
    # 7. Calculate scores
    depth = 0
    depth += min(word_count / 2, 25)           # Max 25 pts for length
    depth += len(mentioned_skills) * 10         # 10 pts per skill
    depth += len(found_actions) * 5             # 5 pts per action
    depth += 15 if has_example else 0           # 15 pts for example
    depth += 10 if has_numbers else 0           # 10 pts for numbers
    
    # STAR bonus
    star_score = sum(star_analysis.values()) * 10 # Max 40 pts
    depth += star_score
    depth = min(int(depth), 100)
    
    return {
        'mentioned_skills': mentioned_skills[:5],
        'found_actions': found_actions[:4],
        'word_count': word_count,
        'has_example': has_example,
        'has_numbers': has_numbers,
        'number_context': number_context[:3],
        'has_positive': has_positive,
        'has_challenge': has_challenge,
        'depth_score': depth,
        'star_analysis': star_analysis
    }


def _build_acknowledgment(analysis, user_msg):
    """
    Build a contextual acknowledgment sentence based on response analysis.
    Returns (english, vietnamese) tuple.
    """
    import random
    skills = analysis['mentioned_skills']
    actions = analysis['found_actions']
    depth = analysis['depth_score']
    word_count = analysis['word_count']
    
    en_parts = []
    vi_parts = []
    
    # --- Depth-based opening ---
    if word_count < 10:
        en_parts.append(random.choice([
            "I'd love to hear more detail.",
            "Could you expand on that a bit?",
            "That's a start — can you elaborate further?"
        ]))
        vi_parts.append("Tôi muốn nghe thêm chi tiết.")
    elif depth >= 70:
        en_parts.append(random.choice([
            "That's an excellent, detailed response!",
            "Very thorough answer — I'm impressed!",
            "Outstanding level of detail!"
        ]))
        vi_parts.append("Câu trả lời rất chi tiết và xuất sắc!")
    elif depth >= 40:
        en_parts.append(random.choice([
            "That's a solid answer.",
            "Good explanation!",
            "Thank you for sharing that."
        ]))
        vi_parts.append("Câu trả lời tốt!")
    else:
        en_parts.append(random.choice([
            "Thank you for your response.",
            "I appreciate you sharing that.",
            "Interesting perspective."
        ]))
        vi_parts.append("Cảm ơn câu trả lời của bạn.")
    
    # --- Skill acknowledgment ---
    if skills:
        if len(skills) >= 3:
            skill_str = ', '.join(f"**{s}**" for s in skills[:3])
            en_parts.append(f"I notice you're well-versed in {skill_str} — that's a strong combination.")
            vi_parts.append(f"Tôi nhận thấy bạn thành thạo {skill_str} — đó là sự kết hợp mạnh mẽ.")
        elif len(skills) >= 1:
            en_parts.append(f"Your experience with **{skills[0]}** is clearly relevant here.")
            vi_parts.append(f"Kinh nghiệm của bạn với **{skills[0]}** rõ ràng rất phù hợp.")
    
    # --- Action verb acknowledgment ---
    if actions and len(actions) >= 2:
        en_parts.append("I can see you've taken real ownership in your work.")
        vi_parts.append("Tôi thấy bạn đã thực sự chủ động trong công việc.")
    
    # --- Example/numbers acknowledgment ---
    if analysis['has_example'] and analysis['has_numbers']:
        en_parts.append("The concrete example with metrics really strengthens your answer.")
        vi_parts.append("Ví dụ cụ thể với số liệu thực sự làm câu trả lời thuyết phục hơn.")
    elif analysis['has_example']:
        en_parts.append("Great use of a specific example to illustrate your point.")
        vi_parts.append("Sử dụng ví dụ cụ thể rất tốt để minh họa.")
    elif analysis['has_numbers']:
        en_parts.append("I like that you quantified your impact — that shows strong analytical thinking.")
        vi_parts.append("Tôi thích việc bạn đưa ra con số — điều đó thể hiện tư duy phân tích tốt.")
    
    # --- STAR Method coaching ---
    star = analysis.get('star_analysis', {})
    if not all(star.values()) and word_count > 20:
        missing = [k for k, v in star.items() if not v]
        labels = {'S': 'Situation', 'T': 'Task', 'A': 'Action', 'R': 'Result'}
        missing_labels = [labels[m] for m in missing]
        
        if 'R' in missing:
            en_parts.append("💡 **Tip**: Don't forget to mention the **Result** or impact of your actions.")
            vi_parts.append("💡 **Mẹo**: Đừng quên nhắc đến **Kết quả** hoặc tác động từ hành động của bạn.")
        elif 'A' in missing:
            en_parts.append("💡 **Tip**: I'd love to hear more about the specific **Actions** you personally took.")
            vi_parts.append("💡 **Mẹo**: Tôi muốn nghe thêm về những **Hành động** cụ thể mà bạn đã trực tiếp thực hiện.")
    
    en = ' '.join(en_parts)
    vi = ' '.join(vi_parts)
    return en, vi


# ── Question bank organized by category ──
INTERVIEW_QUESTIONS = {
    'intro': {
        'en': "To start, could you please introduce yourself and highlight how your experience fits this position?",
        'vi': "Để bắt đầu, bạn vui lòng giới thiệu bản thân và nêu bật kinh nghiệm phù hợp với vị trí này?",
    },
    'skill_deep_1': {
        'en': "Can you describe a specific project where you applied **{skill}** to solve a complex problem? What was the outcome?",
        'vi': "Bạn có thể mô tả một dự án cụ thể mà bạn đã áp dụng **{skill}** để giải quyết vấn đề phức tạp không? Kết quả như thế nào?",
    },
    'skill_deep_2': {
        'en': "How do you typically combine **{skill_1}** and **{skill_2}** in your workflow? Can you give a concrete example?",
        'vi': "Bạn thường kết hợp **{skill_1}** và **{skill_2}** trong quy trình làm việc như thế nào? Bạn có thể cho ví dụ cụ thể không?",
    },
    'behavioral_star': {
        'en': "Tell me about a time you faced a significant technical challenge. What was the **Situation**, your **Task**, the **Action** you took, and the **Result**?",
        'vi': "Hãy kể về một lần bạn đối mặt thử thách kỹ thuật lớn. **Tình huống** là gì, **Nhiệm vụ** của bạn, **Hành động** bạn đã thực hiện, và **Kết quả** ra sao?",
    },
    'technical_design': {
        'en': "For this role, imagine you need to design a system from scratch using **{skill}**. Walk me through your approach.",
        'vi': "Với vị trí này, hãy tưởng tượng bạn cần thiết kế hệ thống từ đầu sử dụng **{skill}**. Hãy trình bày cách tiếp cận của bạn.",
    },
    'teamwork': {
        'en': "How do you handle tight deadlines or shifting priorities? Have you had a disagreement with a colleague? How did you resolve it?",
        'vi': "Bạn xử lý thế nào khi gặp deadline gấp? Bạn đã bao giờ bất đồng với đồng nghiệp chưa? Giải quyết ra sao?",
    },
    'growth': {
        'en': "What do you consider your biggest area for growth? What skill are you currently developing?",
        'vi': "Bạn coi đâu là lĩnh vực cần phát triển nhất? Kỹ năng nào bạn đang phát triển?",
    },
    'motivation': {
        'en': "What motivates you in your career? Why are you interested in this role, and what work environment suits you best?",
        'vi': "Điều gì thúc đẩy bạn trong sự nghiệp? Tại sao bạn quan tâm vị trí này? Môi trường làm việc nào phù hợp nhất?",
    },
    'leadership': {
        'en': "Have you ever led a project or initiative? Tell me about a time you went above and beyond what was expected.",
        'vi': "Bạn đã bao giờ dẫn dắt dự án nào chưa? Hãy kể về lần bạn vượt xa kỳ vọng.",
    },
    'wrapup': {
        'en': "We're nearing the end. Do you have any questions for me about the role, team, or company culture?",
        'vi': "Chúng ta sắp kết thúc. Bạn có câu hỏi nào về vị trí, đội ngũ, hoặc văn hóa công ty không?",
    },
}

QUESTION_ORDER = [
    'intro', 'skill_deep_1', 'skill_deep_2', 'behavioral_star',
    'technical_design', 'teamwork', 'growth', 'motivation', 'leadership', 'wrapup'
]


@app.route('/interview/chat', methods=['POST'])
def interview_chat():
    """Smart Bilingual AI Interview — analyzes user responses with NLP"""
    request_started_at = perf_counter()

    if state.get('cv_text') is None:
        latency_ms = (perf_counter() - request_started_at) * 1000
        app.logger.info("[interview_chat] cv_missing latency_ms=%.2f", latency_ms)
        return jsonify({'reply': "I'm ready to interview you! Please upload your CV first so I can tailor the questions to your experience.\n\n(Tôi đã sẵn sàng phỏng vấn bạn! Vui lòng tải CV lên trước để tôi có thể điều chỉnh câu hỏi phù hợp với kinh nghiệm của bạn.)"})

    data = request.json
    user_msg = data.get('message', '')
    history = data.get('history', [])
    topic_start = data.get('topic_start', None)  # e.g. 'behavioral_star'

    # ── Context from state ──
    user_role = state.get('user_role_can', 'Professional')
    user_skills = list(state.get('user_prob', {}).keys())
    
    target_job = "the position"
    if state.get('scores') and len(state['scores']) > 0:
        target_job = state['job_info'][state['scores'][0][0]]['title']

    turn_count = len([h for h in history if h.get('role') == 'user'])
    
    skill_1 = user_skills[0] if len(user_skills) > 0 else 'your primary skill'
    skill_2 = user_skills[1] if len(user_skills) > 1 else 'another technical area'
    skill_3 = user_skills[2] if len(user_skills) > 2 else 'a relevant tool'

    # ── Analyze user's previous response ──
    analysis = _analyze_response(user_msg, user_skills) if user_msg != 'init_interview' else None
    
    # ── Check if response is too shallow (greeting, "ok", "yes", etc.) ──
    is_shallow = False
    if analysis and analysis['depth_score'] < 15 and analysis['word_count'] < 10:
        is_shallow = True

    # ── Compute effective_turn: shallow responses don't advance the question ──
    # Count how many previous user messages were also shallow (from history)
    effective_turn = turn_count
    if is_shallow and turn_count > 0:
        effective_turn = max(turn_count - 1, 0)  # Stay on current question
    
    # ── Build reply ── 
    if turn_count == 0:
        # Opening — no analysis needed
        reply = (f"Hello! I am your AI Interviewer. Based on your profile, I see you have a strong background as a **{user_role}**. "
                 f"We are considering you for the **{target_job}** role.\n\n"
                 f"(Chào bạn! Tôi là Người phỏng vấn AI. Dựa trên hồ sơ của bạn, tôi thấy bạn có nền tảng vững chắc là **{user_role}**. "
                 f"Chúng tôi đang xem xét bạn cho vị trí **{target_job}**.)\n\n")
        q = INTERVIEW_QUESTIONS['intro']
        reply += f"{q['en']}\n\n({q['vi']})"

    elif topic_start and topic_start in INTERVIEW_QUESTIONS:
        # ── Topic chip was clicked: jump directly to that question ──
        ack_en, ack_vi = _build_acknowledgment(analysis, user_msg) if analysis else ("Great!", "Tuyệt!")
        q = INTERVIEW_QUESTIONS[topic_start]
        q_en = q['en'].format(skill=skill_1, skill_1=skill_1, skill_2=skill_2, skill_3=skill_3)
        q_vi = q['vi'].format(skill=skill_1, skill_1=skill_1, skill_2=skill_2, skill_3=skill_3)
        reply = f"{ack_en}\n\n{q_en}\n\n({ack_vi}\n\n{q_vi})"

    elif is_shallow:
        # ── Response too short / just a greeting — re-ask the current question ──
        import random
        prev_q_key = QUESTION_ORDER[min(effective_turn, len(QUESTION_ORDER) - 1)]
        prev_q = INTERVIEW_QUESTIONS[prev_q_key]
        prev_q_en = prev_q['en'].format(skill=skill_1, skill_1=skill_1, skill_2=skill_2, skill_3=skill_3)
        prev_q_vi = prev_q['vi'].format(skill=skill_1, skill_1=skill_1, skill_2=skill_2, skill_3=skill_3)
        
        nudge_en = random.choice([
            "I appreciate that! But could you go into more detail?",
            "Thanks! I'd love to hear a more detailed answer.",
            "Got it! Could you elaborate a bit more on that?",
            "I see! Can you share more specifics so I can understand your experience better?",
        ])
        nudge_vi = random.choice([
            "Cảm ơn! Nhưng bạn có thể trả lời chi tiết hơn không?",
            "Tôi hiểu! Bạn có thể chia sẻ thêm chi tiết không?",
            "Tốt! Bạn có thể nói rõ hơn một chút không?",
        ])
        
        reply = (f"{nudge_en}\n\n"
                 f"💡 **Tip**: Try to include specific examples, tools you used, and measurable outcomes.\n\n"
                 f"{prev_q_en}\n\n"
                 f"({nudge_vi}\n\n"
                 f"💡 **Mẹo**: Hãy thử đưa vào ví dụ cụ thể, công cụ đã dùng, và kết quả đo lường được.\n\n"
                 f"{prev_q_vi})")

    elif effective_turn >= 10:
        # Final
        ack_en, ack_vi = _build_acknowledgment(analysis, user_msg)
        reply = (f"{ack_en}\n\nThank you for your time! This has been a very productive interview. "
                 "You can click **\"End Session\"** to see your summary.\n\n"
                 f"({ack_vi}\n\nCảm ơn bạn! Đây là buổi phỏng vấn rất hiệu quả. "
                 "Nhấn **\"End Session\"** để xem tóm tắt.)")
    
    else:
        # ── Smart response: Acknowledgment + Next Question ──
        ack_en, ack_vi = _build_acknowledgment(analysis, user_msg)
        
        # Determine next question category
        q_key = QUESTION_ORDER[min(effective_turn, len(QUESTION_ORDER) - 1)]
        q = INTERVIEW_QUESTIONS[q_key]
        
        # Format question with skill placeholders
        q_en = q['en'].format(skill=skill_1, skill_1=skill_1, skill_2=skill_2, skill_3=skill_3)
        q_vi = q['vi'].format(skill=skill_1, skill_1=skill_1, skill_2=skill_2, skill_3=skill_3)
        
        # If user mentioned skills in their answer, dynamically adjust the next skill question
        if q_key in ('skill_deep_1', 'skill_deep_2', 'technical_design') and analysis['mentioned_skills']:
            # Ask about a skill they DIDN'T mention yet for variety
            unmentioned = [s for s in user_skills[:6] if s.lower() not in 
                          [ms.lower() for ms in analysis['mentioned_skills']]]
            if unmentioned:
                pick = unmentioned[0]
                q_en = q['en'].format(skill=pick, skill_1=pick, skill_2=skill_2, skill_3=skill_3)
                q_vi = q['vi'].format(skill=pick, skill_1=pick, skill_2=skill_2, skill_3=skill_3)
        
        reply = f"{ack_en}\n\n{q_en}\n\n({ack_vi}\n\n{q_vi})"
    
    latency_ms = (perf_counter() - request_started_at) * 1000
    app.logger.info(
        "[interview_chat] latency_ms=%.2f shallow=%s turn=%s topic_start=%s",
        latency_ms,
        is_shallow,
        turn_count + 1,
        topic_start
    )

    return jsonify({
        'reply': reply,
        'turn': turn_count + 1,
        'total_turns': 10,
        'analysis': analysis,
        'shallow': is_shallow  # Tell frontend this was a shallow response
    })


@app.route('/interview/summary', methods=['POST'])
def interview_summary():
    """Generate interview assessment summary"""
    data = request.json
    history = data.get('history', [])
    
    user_role = state.get('user_role_can', 'Professional')
    user_skills = list(state.get('user_prob', {}).keys())[:8]
    
    target_job = "the position"
    match_score = 0
    if state.get('scores') and len(state['scores']) > 0:
        target_job = state['job_info'][state['scores'][0][0]]['title']
        match_score = round(state['scores'][0][1] * 100, 1)
    
    user_turns = [h for h in history if h.get('role') == 'user']
    ai_turns = [h for h in history if h.get('role') == 'ai']
    questions_answered = len(user_turns)
    
    # Determine covered topics based on turn count
    topics = []
    topic_labels = [
        "Self Introduction", "Skill Deep-Dive", "Multi-Skill Integration",
        "Behavioral (STAR)", "Technical Design", "Teamwork & Communication",
        "Growth Areas", "Motivation & Culture", "Leadership", "Q&A"
    ]
    for i in range(min(questions_answered, len(topic_labels))):
        topics.append(topic_labels[i])
    
    # 1. Technical Score (Depth)
    tech_depths = [h.get('analysis', {}).get('depth_score', 0) for h in user_turns if h.get('analysis')]
    avg_tech = sum(tech_depths)/len(tech_depths) if tech_depths else 0
    
    # 2. Communication Score (Word count & Variety)
    word_counts = [len(h.get('content', '').split()) for h in user_turns]
    avg_words = round(sum(word_counts)/len(word_counts), 1) if word_counts else 0
    comm_variety = [len(set(h.get('content', '').split())) for h in user_turns]
    avg_comm = min((sum(comm_variety)/len(comm_variety))/30 * 100, 100) if comm_variety else 0
    
    # 3. Confidence/Structure (STAR check)
    stars_found = 0
    total_star_possible = questions_answered * 4
    for h in user_turns:
        if h.get('analysis') and h.get('analysis').get('star_analysis'):
            stars_found += sum(h['analysis']['star_analysis'].values())
    star_score = (stars_found / total_star_possible * 100) if total_star_possible > 0 else 0

    # Assessment logic
    overall = (avg_tech * 0.5) + (avg_comm * 0.2) + (star_score * 0.3)
    
    if overall > 80:
        assessment = "Expert"
        feedback = "Outstanding performance! You provided deep technical insights and structured your answers perfectly using the STAR method."
        feedback_vi = "Tâm điểm tuyệt vời! Bạn đã đưa ra những hiểu biết kỹ thuật sâu sắc và cấu trúc câu trả lời hoàn hảo bằng phương pháp STAR."
    elif overall > 60:
        assessment = "Strong"
        feedback = "Very good session. You demonstrated solid technical knowledge and clear communication."
        feedback_vi = "Buổi phỏng vấn rất tốt. Bạn đã thể hiện kiến thức kỹ thuật vững chắc và khả năng giao tiếp rõ ràng."
    elif overall > 40:
        assessment = "Average"
        feedback = "Decent start. Try to provide more concrete examples and quantitative results in your future sessions."
        feedback_vi = "Khởi đầu khá ổn. Hãy cố gắng đưa ra nhiều ví dụ cụ thể và kết quả đo lường được trong các buổi tới."
    else:
        assessment = "Developing"
        feedback = "Focus on elaborating more on your actions and the specific impact you had in projects."
        feedback_vi = "Hãy tập trung vào việc mô tả chi tiết hơn các hành động và tác động cụ thể của bạn trong các dự án."

    return jsonify({
        'questions_answered': questions_answered,
        'topics_covered': topics,
        'assessment': assessment,
        'scores': {
            'technical': round(avg_tech, 1),
            'communication': round(avg_comm, 1),
            'structure': round(star_score, 1),
            'overall': round(overall, 1)
        },
        'feedback': feedback,
        'feedback_vi': feedback_vi,
        'detected_skills': list(set([s for h in user_turns if h.get('analysis') for s in h['analysis'].get('mentioned_skills', [])])),
        'avg_response_words': avg_words,
        'target_job': target_job,
        'match_score': match_score,
        'top_skills': user_skills,
        'role': user_role
    })

@app.route('/api/user-profile')
def user_profile():
    """Get summarized user profile for UI widgets"""
    if state.get('cv_text') is None:
        return jsonify({'active': False})
    
    target_job = "N/A"
    match_score = 0
    if state.get('scores') and len(state['scores']) > 0:
        best_job_id = state['scores'][0][0]
        target_job = state['job_info'][best_job_id]['title']
        match_score = state['scores'][0][1]

    return jsonify({
        'active': True,
        'role': state.get('user_role_can', 'Unknown'),
        'skills_count': len(state.get('user_prob', {})),
        'target_job': target_job,
        'match_score': round(match_score * 100, 1),
        'city': state.get('user_city', 'Unknown')
    })

@app.route('/api/cv-data')
def cv_data():
    """Extract structured CV data for the CV Builder auto-fill"""
    if state.get('cv_text') is None:
        return jsonify({'active': False})
    
    cv_text = state['cv_text']
    
    # ── Extract personal info using regex ──
    # Email
    email_match = re.search(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}', cv_text)
    email = email_match.group(0) if email_match else ''
    
    # Phone (Vietnamese & international formats)
    phone_match = re.search(r'(?:\+84|0)\s*\d[\d\s.\-]{7,12}', cv_text)
    phone = re.sub(r'\s+', '', phone_match.group(0)) if phone_match else ''
    
    # Name: try first non-empty line that looks like a name (2-4 capitalized words)
    name = ''
    for line in cv_text.split('\n')[:10]:
        line = line.strip()
        if not line or '@' in line or line.startswith('http') or len(line) > 60:
            continue
        words = line.split()
        if 2 <= len(words) <= 5 and all(w[0].isupper() for w in words if w.isalpha()):
            name = line
            break
    
    # LinkedIn
    linkedin_match = re.search(r'(?:linkedin\.com/in/|linkedin:\s*)(\S+)', cv_text, re.IGNORECASE)
    linkedin = f"linkedin.com/in/{linkedin_match.group(1)}" if linkedin_match else ''
    
    # ── Skills ──
    skills = list(state.get('user_prob', {}).keys())
    
    # ── Role / Title ──
    role = state.get('user_role_can', '')
    
    # ── Location ──
    city = state.get('user_city', '')
    
    # ── Summary: take first paragraph-like block that's > 50 chars ──
    summary = ''
    lines = cv_text.split('\n')
    for i, line in enumerate(lines):
        line = line.strip()
        if len(line) > 50 and not re.match(r'^[\w\s]{1,20}:$', line):
            # Skip lines that are mostly special chars or headers
            alpha_ratio = sum(1 for c in line if c.isalpha()) / max(len(line), 1)
            if alpha_ratio > 0.5:
                summary = line
                break
    
    # ── Education: look for university/college keywords ──
    edu_school = ''
    edu_major = ''
    edu_patterns = [
        r'(?:university|đại học|college|học viện|trường)[^\n]{0,80}',
        r'(?:bachelor|master|cử nhân|thạc sĩ|kỹ sư|engineer)[^\n]{0,80}'
    ]
    for pat in edu_patterns:
        m = re.search(pat, cv_text, re.IGNORECASE)
        if m:
            found = m.group(0).strip()
            if not edu_school:
                edu_school = found
            elif not edu_major:
                edu_major = found
            
    # ── Experience: look for job title patterns ──
    exp_role = role if role else ''
    exp_company = ''
    exp_desc = ''
    
    # Look for company names near role mentions
    company_patterns = [
        r'(?:at|tại|@)\s+([A-Z][A-Za-z\s&.]+(?:Inc|Corp|Ltd|LLC|Co|Company|Group|JSC|Technology|Solutions|Vietnam)?)',
        r'(?:company|công ty)[:\s]+([^\n]+)',
    ]
    for pat in company_patterns:
        m = re.search(pat, cv_text, re.IGNORECASE)
        if m:
            exp_company = m.group(1).strip()[:50]
            break
    
    # Look for bullet-point descriptions
    bullet_lines = []
    for line in lines:
        line = line.strip()
        if line.startswith(('•', '-', '●', '○', '▪', '*')) and len(line) > 10:
            bullet_lines.append(line)
            if len(bullet_lines) >= 5:
                break
    exp_desc = '\n'.join(bullet_lines) if bullet_lines else ''
    
    return jsonify({
        'active': True,
        'name': name,
        'title': role,
        'email': email,
        'phone': phone,
        'linkedin': linkedin,
        'location': city,
        'summary': summary,
        'skills': ', '.join(skills[:15]),
        'exp_role': exp_role,
        'exp_company': exp_company,
        'exp_desc': exp_desc,
        'edu_school': edu_school,
        'edu_major': edu_major,
    })


@app.route('/api/salary-estimate', methods=['POST'])
def salary_estimate():
    """Estimate salary based on role, experience, and skills from DB"""
    data = request.json
    role_query = data.get('role', '').lower()
    exp_year = int(data.get('exp', 0))
    location = data.get('location', '').lower()
    skills = data.get('skills', [])

    if state['df'] is None:
        return jsonify({
            'min': 1000 + (exp_year * 200),
            'max': 1800 + (exp_year * 300),
            'currency': 'USD (Est.)'
        })

    df = state['df']
    mask_role = df['job_title'].str.lower().str.contains(role_query, na=False)
    
    if 'remote' in location:
        mask_loc = df['location'].str.lower().str.contains('remote', na=False)
    elif location:
         mask_loc = df['location'].str.lower().str.contains(location, na=False)
    else:
        mask_loc = True

    subset = df[mask_role & mask_loc]
    if len(subset) < 3:
        subset = df[mask_role]

    if len(subset) == 0:
        return jsonify({'min': 1000, 'max': 2000, 'currency': 'USD'})

    salaries = []
    import re
    def parse_salary_str(s):
        s = str(s).lower().strip()
        if not s or 'thỏa thuận' in s: return None
        is_usd = 'usd' in s or '$' in s
        scale = 25000 if is_usd else 1000000 
        nums = re.findall(r'(\d+[.,]?\d*)', s.replace('.', '').replace(',', ''))
        nums = [float(n) for n in nums]
        if not nums: return None
        if len(nums) == 1:
             val = nums[0] * scale
             return (val, val)
        elif len(nums) >= 2:
             v1 = nums[0] * scale
             v2 = nums[1] * scale
             return (v1, v2)
        return None

    for s_str in subset['salary']:
        parsed = parse_salary_str(s_str)
        if parsed: salaries.append(parsed)
            
    if not salaries:
         return jsonify({'min': 1200, 'max': 2400, 'currency': 'USD'})

    mins = [s[0] for s in salaries]
    maxs = [s[1] for s in salaries]
    
    avg_min = np.mean(mins)
    avg_max = np.mean(maxs)
    
    # Experience Multiplier
    exp_multiplier = 0.7 + (exp_year * 0.1) # 10% increase per year
    exp_multiplier = min(max(exp_multiplier, 0.7), 2.5)
    
    # Skills Bonus (5% per selected skill, max 20%)
    skill_bonus = 1.0 + (min(len(skills), 4) * 0.05)
    
    final_min = (avg_min * exp_multiplier) / 25000
    final_max = (avg_max * exp_multiplier * skill_bonus) / 25000
    
    return jsonify({
        'min': int(final_min),
        'max': int(final_max),
        'currency': 'USD',
        'count': len(salaries)
    })

@app.route('/api/featured-jobs')
def featured_jobs():
    """Get featured job opportunities for home page"""
    if state['df'] is None:
        return jsonify({'jobs': []})
    
    df = state['df']
    
    # Get 6 random jobs (to have variety on refresh)
    sample_size = min(6, len(df))
    sampled_df = df.sample(n=sample_size)
    
    jobs = []
    for _, row in sampled_df.iterrows():
        # Determine job type badge
        location_lower = str(row.get('location', '')).lower()
        job_type_lower = str(row.get('job_type', '')).lower()
        
        if 'remote' in location_lower or 'từ xa' in location_lower:
            work_type = 'Remote'
            badge_class = 'bg-success bg-opacity-10 text-success'
        elif 'hybrid' in job_type_lower:
            work_type = 'Hybrid'
            badge_class = 'bg-primary bg-opacity-10 text-primary'
        else:
            work_type = 'On-site'
            badge_class = 'bg-warning bg-opacity-10 text-warning'
        
        # Get skills (first 3)
        skills_str = str(row.get('skills', ''))
        skills_list = [s.strip() for s in skills_str.split(',') if s.strip()][:3]
        if not skills_list:
            # Try to extract from requirements
            req_str = str(row.get('requirements', ''))
            common_skills = ['Python', 'Java', 'JavaScript', 'SQL', 'AWS', 'React', 'Node.js', 'Docker']
            skills_list = [s for s in common_skills if s.lower() in req_str.lower()][:3]
        
        jobs.append({
            'id': row.get('job_id', ''),
            'title': row.get('job_title', 'Unknown Role'),
            'company': row.get('company', 'Unknown Company'),
            'location': row.get('location', 'Vietnam'),
            'salary': row.get('salary', 'Thỏa thuận'),
            'url': row.get('job_url', '#'),
            'work_type': work_type,
            'badge_class': badge_class,
            'skills': skills_list
        })
    
    return jsonify({'jobs': jobs[:3]})  # Return only 3 jobs

@app.route('/api/search')
def api_search():
    """Real-time job search with advanced filtering and sorting"""
    query = request.args.get('q', '').lower()
    city = request.args.get('city', 'All Locations').lower()
    offset = int(request.args.get('offset', 0))
    limit = int(request.args.get('limit', 20))
    exp_levels = request.args.get('exp', '') # e.g. "intern,junior,senior,lead"
    job_types = request.args.get('type', '') # e.g. "full,part,remote"
    min_salary = int(request.args.get('min_salary', 0))
    sort_by = request.args.get('sort', 'newest')  # newest, relevance, salary
    
    if state['df'] is None:
        return jsonify({'jobs': [], 'has_more': False, 'total': 0})

    df = state['df']
    mask = pd.Series([True] * len(df))

    # 1. Keyword Search (support multiple keywords, all must match)
    if query:
        import re
        # Escape special regex characters in query
        query_escaped = re.escape(query)
        # Split into multiple keywords
        keywords = [kw.strip() for kw in query.split() if kw.strip()]
        
        search_cols = ['job_title', 'company', 'requirements', 'job_desc', 'skills', 'benefits', 'location']
        
        for keyword in keywords:
            keyword_escaped = re.escape(keyword.lower())
            kw_mask = pd.Series([False] * len(df))
            for col in search_cols:
                if col in df.columns:
                    kw_mask |= df[col].astype(str).str.lower().str.contains(keyword_escaped, na=False, regex=True)
            mask &= kw_mask

    # 2. City Filter
    if city != 'all locations':
        if city == 'remote':
            mask &= df['location'].str.lower().str.contains('remote', na=False)
        else:
            mask &= df['location'].str.lower().str.contains(city, na=False)

    # 3. Job Type Filter (Only apply if NOT all options selected)
    if job_types:
        type_list = [t.strip() for t in job_types.split(',') if t.strip()]
        # If all 4 types selected, skip filter (means "All")
        if len(type_list) < 4:
            t_mask = pd.Series([False] * len(df))
            for t in type_list:
                if t == 'full': 
                    t_mask |= df['job_type'].str.lower().str.contains('toàn thời gian|full|fulltime|full-time', na=False, regex=True)
                elif t == 'part': 
                    t_mask |= df['job_type'].str.lower().str.contains('bán thời gian|part|parttime|part-time', na=False, regex=True)
                elif t == 'remote': 
                    t_mask |= df['location'].str.lower().str.contains('remote|từ xa|work from home|wfh', na=False, regex=True)
                elif t == 'contract': 
                    t_mask |= df['job_type'].str.lower().str.contains('thực tập|hợp đồng|freelance|contract|intern', na=False, regex=True)
            mask &= t_mask

    # 4. Experience Filter (Only apply if NOT all options selected)
    if exp_levels:
        exp_list = [e.strip() for e in exp_levels.split(',') if e.strip()]
        # If all 4 experience levels selected, skip filter (means "All")
        if len(exp_list) < 4:
            exp_mask = pd.Series([False] * len(df))
            for level in exp_list:
                if level == 'intern':
                    exp_mask |= df['job_title'].str.lower().str.contains('intern|fresher|thực tập|mới tốt nghiệp|sinh viên', na=False, regex=True)
                elif level == 'junior':
                    exp_mask |= df['job_title'].str.lower().str.contains('junior|entry|nhân viên|nv|1 năm|2 năm|1-2', na=False, regex=True)
                elif level == 'senior':
                    exp_mask |= df['job_title'].str.lower().str.contains('senior|expert|middle|chuyên gia|3 năm|4 năm|5 năm', na=False, regex=True)
                elif level == 'lead':
                    exp_mask |= df['job_title'].str.lower().str.contains('lead|manager|head|director|trưởng|giám đốc|quản lý', na=False, regex=True)
            mask &= exp_mask

    filtered_df = df[mask]
    
    # 5. Salary Filter
    if min_salary > 0:
        def check_salary(s_str):
            import re
            s_str = str(s_str).lower()
            if 'thỏa thuận' in s_str: return True
            nums = re.findall(r'(\d+)', s_str.replace('.', '').replace(',', ''))
            if not nums: return True
            is_usd = 'usd' in s_str or '$' in s_str
            val = float(nums[-1])
            if not is_usd: val = val / 25 
            return val >= min_salary
        
        filtered_df = filtered_df[filtered_df['salary'].apply(check_salary)]

    # 6. Sorting
    if sort_by == 'newest':
        # Sort by id descending (higher id = newer job)
        if 'id' in filtered_df.columns:
            filtered_df = filtered_df.sort_values('id', ascending=False)
        else:
            filtered_df = filtered_df.iloc[::-1]  # Reverse order as fallback
    elif sort_by == 'salary':
        # Sort by salary (high to low)
        def extract_max_salary(s_str):
            import re
            s_str = str(s_str).lower()
            if 'thỏa thuận' in s_str: return 0
            nums = re.findall(r'(\d+)', s_str.replace('.', '').replace(',', ''))
            if not nums: return 0
            is_usd = 'usd' in s_str or '$' in s_str
            val = float(nums[-1])
            if not is_usd: val = val / 25
            return val
        filtered_df = filtered_df.copy()
        filtered_df['_sort_salary'] = filtered_df['salary'].apply(extract_max_salary)
        filtered_df = filtered_df.sort_values('_sort_salary', ascending=False)
        filtered_df = filtered_df.drop(columns=['_sort_salary'])
    # else: relevance - keep original order

    total_count = len(filtered_df)
    results = filtered_df.iloc[offset : offset + limit]
    
    output = []
    for _, row in results.iterrows():
        output.append({
            'id': row.get('id', ''),
            'title': row.get('job_title', 'Unknown Role'),
            'company': row.get('company', 'Unknown Company'),
            'location': row.get('location', 'Remote'),
            'salary': row.get('salary', 'Thỏa thuận'),
            'url': row.get('job_url', '#'),
            'type': 'Full-time'
        })
    
    if output:
        log_activity('match', 'Global Search', f"Found {total_count} jobs matching '{query}'")
        db_data = load_dashboard_data()
        db_data['stats']['matches'] += (1 if offset == 0 else 0) # Only count initial search
        save_dashboard_data(db_data)

    return jsonify({
        'jobs': output,
        'has_more': (offset + limit) < total_count,
        'total': total_count
    })


def init_application():
    try:
        excel_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'db_job_tuan.xlsx')
        if not os.path.exists(excel_path):
            print(f"[ERROR] db_job_tuan.xlsx not found at {excel_path}. Please ensure the file exists.")
            return
        print("[INFO] Initializing NCKH Job Matching System...")
        
        # 1. Load Excel Data
        _, df = load_excel_file(excel_path)
        
        state['df'] = df
        
        # 2. Build Base Job Graph
        G = nx.DiGraph()
        init_rdf_graph()
        job_info = {}
        job_nodes, job_info = build_job_nodes(G, df, job_info)
        state['G'] = G
        state['job_nodes'] = job_nodes
        state['job_info'] = job_info
        
        # 3. Pre-compute TF-IDF for all jobs
        print("Pre-computing TF-IDF vectors...")
        valid_job_nodes = [j for j in job_nodes if j in job_info]
        texts = [job_info[j]["text"] for j in valid_job_nodes]
        
        tfidf = TfidfVectorizer(
            analyzer="char_wb", ngram_range=(3, 5),
            min_df=1, max_df=1.0, max_features=12000,
            sublinear_tf=True, lowercase=True
        )
        X = tfidf.fit_transform(texts)
        X = normalize(X)
        
        state['tfidf'] = tfidf
        state['X'] = X
        state['IDX'] = {j: i for i, j in enumerate(valid_job_nodes)}
        state['valid_job_nodes'] = valid_job_nodes
        
        # 4. Pre-compute Job-to-Job Similarities (SIMILAR_TO edges)
        print("Pre-calculating job-job similarities...")
        sim_edge_count = build_job_job_similar_edges(G, valid_job_nodes, job_info, state['IDX'], X)
        print(f"Added {sim_edge_count} SIMILAR_TO edges.")
        
        print("[SUCCESS] System Ready. Server starting on http://127.0.0.1:5000")
        state['is_ready'] = True
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"[ERROR] Failed to initialize: {e}")


if __name__ == "__main__":
    init_application()
    app.run(host="127.0.0.1", port=5000, debug=True)
