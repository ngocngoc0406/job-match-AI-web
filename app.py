# -*- coding: utf-8 -*-
"""Flask web application for NCKH job matching system"""

from flask import Flask, render_template, request, jsonify, send_file
import os
import json
from werkzeug.utils import secure_filename
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize

from config import (
    TOPK_USER_JOB, CORE_SKILLS_CANON, SIM_THRESHOLD, 
    CANDIDATES_TOP, TOPK_SIMILAR, MIN_KEEP_PROB
)
from data_loader import load_excel_file, load_pdf_file, extract_all_text_from_pdf
from text_processing import (
    norm_text, infer_role_canonical, parse_year_range, exp_bucket, 
    parse_location_city_detail, short_label
)
from skill_extraction import extract_skills_probabilistic
from graph_visualization import clean_focus_layout
from graph_builder import build_job_nodes, build_user_node, init_rdf_graph, build_strict_user_job_graph,build_strict_user_job_graph
from matching import compute_user_job_scores, explain_user_job, build_job_job_similar_edges
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
    'G': None,
    'tfidf': None,
    'X': None,
    'IDX': None,
    'cv_vec': None,
    'valid_job_nodes': None,
}

@app.route('/')
def index():
    """Home page"""
    return render_template('index.html')

@app.route('/upload_page')
def upload_page():
    return render_template('pages/upload.html')

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

@app.route('/upload', methods=['POST'])
def upload_files():
    """Handle file uploads"""
    try:
        pdf_file = request.files.get('pdf_file')

        # Check if PDF file is provided
        if not pdf_file:
            return jsonify({'error': 'PDF file required'}), 400

        # Always use default Excel file
        excel_path = os.path.join(os.path.dirname(__file__), 'db_job_tuan.xlsx')
        if not os.path.exists(excel_path):
            return jsonify({'error': 'Default job database (db_job_tuan.xlsx) not found'}), 400

        # Save PDF temporarily
        pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(pdf_file.filename))
        pdf_file.save(pdf_path)

        # Load data
        _, df = load_excel_file(excel_path)
        cv_text = extract_all_text_from_pdf(pdf_path, verbose=False)

        # Store in state
        state['df'] = df
        state['cv_text'] = cv_text

        # Initialize graph
        G = nx.DiGraph()
        rdf, EX = init_rdf_graph()
        state['G'] = G

        # Build job nodes
        job_info = {}
        job_nodes, job_info = build_job_nodes(G, df, job_info)
        state['job_nodes'] = job_nodes
        state['job_info'] = job_info

        # Build user node
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

        # Build TF-IDF
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

        cv_vec = normalize(tfidf.transform([norm_text(cv_text)]))
        state['cv_vec'] = cv_vec

        # Compute scores
        scores = compute_user_job_scores(
            job_nodes, job_info, user_prob, user_city, user_detail,
            state['IDX'], X, cv_vec, tfidf, state['user_role_can'], 
            state['user_exp_bucket'], user_raw2can_best, user_raw2can_map
        )
        state['scores'] = scores

        # Add MATCHES_JOB edges to graph with scores
        for job_node, score, explain in scores:
            G.add_edge(USER_ID, job_node, rel="MATCHES_JOB", score=round(score, 3))

        # Build SIMILAR_TO edges between jobs using collab.py logic
        sim_edge_count = build_job_job_similar_edges(G, valid_job_nodes, job_info, state['IDX'], X)
        print(f"Added {sim_edge_count} SIMILAR_TO edges between jobs")

        # Clean up uploaded PDF file
        os.remove(pdf_path)

        return jsonify({
            'success': True,
            'jobs_count': len(job_nodes),
            'skills_detected': len(user_prob),
            'user_city': user_city,
            'user_role': state['user_role_can']
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/results')
def results():
    """Display matching results"""
    if state['scores'] is None:
        return jsonify({'error': 'No results available'}), 400

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
    if state.get('G') is None or state.get('cv_text') is None:
        return jsonify({'error': 'No graph available. Please upload a CV first.'}), 400

    try:
        G = state['G']
        USER_ID = state.get('USER_ID')

        # --- chọn center node (giữ logic cũ của bạn)
        center_node = USER_ID

        # --- build focus subgraph (logic chuẩn của bạn)
        H = build_strict_user_job_graph(
            G,
            user_node=USER_ID,
            topk=TOPK_USER_JOB
        )

        # --- layout
        from graph_visualization import clean_focus_layout
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

@app.route('/interview/chat', methods=['POST'])
def interview_chat():
    """Mock AI Interview Endpoint"""
    # In a real scenario, this would call OpenAI/Gemini/Claude
    data = request.json
    user_msg = data.get('message', '').lower()
    
    # Simple rule-based logic for demo
    if 'intro' in user_msg or 'myself' in user_msg:
        reply = "Thank you. That's a strong background. What specific experience do you have with Python and Flask?"
    elif 'python' in user_msg or 'flask' in user_msg:
        reply = "Excellent. Can you describe a challenging bug you encountered in a recent project and how you solved it?"
    elif 'bug' in user_msg or 'solve' in user_msg:
        reply = "Problem-solving is key. Now, how do you handle tight deadlines and pressure in a team environment?"
    elif 'deadline' in user_msg or 'pressure' in user_msg:
        reply = "That's good to hear. Do you have any questions for us about the company or the role?"
    else:
        reply = "That's interesting. Could you elaborate a bit more on that point?"

    import time
    time.sleep(1.5) # Simulate AI thinking
    
    return jsonify({'reply': reply})

@app.route('/api/salary-estimate', methods=['POST'])
def salary_estimate():
    """Estimate salary based on role and experience from DB"""
    data = request.json
    role_query = data.get('role', '').lower()
    exp_year = int(data.get('exp', 0))
    location = data.get('location', '').lower()

    if state['df'] is None:
         # Fallback if DB not loaded
        return jsonify({
            'min': 1000 + (exp_year * 200),
            'max': 1800 + (exp_year * 300),
            'currency': 'USD (Est.)',
            'note': 'Database not loaded, using heuristic.'
        })

    df = state['df']
    
    # 1. Filter by Role
    # Simple keyword match
    mask_role = df['job_title'].str.lower().str.contains(role_query, na=False)
    
    # 2. Filter by Location (Optional)
    if 'remote' in location:
        mask_loc = df['location'].str.lower().str.contains('remote', na=False)
    elif location:
         mask_loc = df['location'].str.lower().str.contains(location, na=False)
    else:
        mask_loc = True

    subset = df[mask_role & mask_loc]
    
    if len(subset) < 3:
        # Fallback to just role if location is too specific
        subset = df[mask_role]

    if len(subset) == 0:
        return jsonify({
            'min': 1000,
            'max': 2000,
            'currency': 'USD',
            'note': 'No matching data found.'
        })

    # 3. Parse Salaries
    # Expected formats: "10 - 20 triệu", "Up to 3000 USD", "Thỏa thuận"
    salaries = []
    
    import re
    
    def parse_salary_str(s):
        s = str(s).lower().strip()
        if not s or 'thỏa thuận' in s:
            return None
            
        # Detect currency
        is_usd = 'usd' in s or '$' in s
        scale = 25000 if is_usd else 1000000 # Convert all to VND for calc
        
        # Extract numbers
        nums = re.findall(r'(\d+[.,]?\d*)', s.replace('.', '').replace(',', ''))
        nums = [float(n) for n in nums]
        
        if not nums:
            return None
            
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
        if parsed:
            salaries.append(parsed)
            
    if not salaries:
         return jsonify({
            'min': 1000,
            'max': 2000,
            'currency': 'USD',
            'note': 'Data available but no salary info.'
        })

    # 4. Calculate Stats
    # Convert VND back to USD approx (1 USD = 25000 VND)
    mins = [s[0] for s in salaries]
    maxs = [s[1] for s in salaries]
    
    avg_min = np.mean(mins)
    avg_max = np.mean(maxs)
    
    # Adjust for experience (simple heuristic multiplier)
    # Assume DB average is for "middle" level ~3 years
    # If user has 0 exp, * 0.7. If 10 exp, * 1.5
    exp_multiplier = 0.7 + (exp_year * 0.08)
    exp_multiplier = min(max(exp_multiplier, 0.7), 2.0)
    
    final_min = (avg_min * exp_multiplier) / 25000
    final_max = (avg_max * exp_multiplier) / 25000
    
    return jsonify({
        'min': int(final_min),
        'max': int(final_max),
        'currency': 'USD',
        'count': len(salaries)
    })

if __name__ == '__main__':
    # Load DB on start if exists
    try:
        excel_path = os.path.join(os.path.dirname(__file__), 'db_job_tuan.xlsx')
        if os.path.exists(excel_path):
            print("Loading DB...")
            _, df = load_excel_file(excel_path)
            
            # OPTIMIZATION: Limit to 50 rows for demo speed
            print(f"Original DB size: {len(df)}")
            if len(df) > 50:
                print("Limiting to 50 rows for faster startup...")
                df = df.head(50)
            
            state['df'] = df
            
            # Build Graph
            G = nx.DiGraph()
            init_rdf_graph()
            state['G'] = G
            build_job_nodes(G, df, {})
            print("DB Loaded.")
    except Exception as e:
        print(f"Error loading DB on start: {e}")

    app.run(debug=True, host='0.0.0.0', port=5000)
