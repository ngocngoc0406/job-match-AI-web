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
    'G': None,          # Base job graph
    'current_G': None,  # Working graph (User + Jobs)
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

        # 1. Load CV text (Speed: depends on PDF size/OCR)
        cv_text = extract_all_text_from_pdf(pdf_path, verbose=False)
        state['cv_text'] = cv_text

        # 2. Get pre-computed data from state (Speed: FAST, O(1))
        job_info = state['job_info']
        job_nodes = state['job_nodes']
        valid_job_nodes = state['valid_job_nodes']
        tfidf = state['tfidf']
        X = state['X']
        IDX = state['IDX']
        
        # 3. Create a clean working graph from the base job graph (Speed: FAST)
        G = state['G'].copy()
        state['current_G'] = G

        # 4. Build user node and extract skills (Speed: moderate, depends on CV)
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

        # 5. Transform CV text to TF-IDF (Speed: FAST, O(phrase_len))
        cv_vec = normalize(tfidf.transform([norm_text(cv_text)]))
        state['cv_vec'] = cv_vec

        # 6. Compute user-job match scores (Speed: moderate, O(N_jobs))
        scores = compute_user_job_scores(
            job_nodes, job_info, user_prob, user_city, user_detail,
            IDX, X, cv_vec, tfidf, state['user_role_can'], 
            state['user_exp_bucket'], user_raw2can_best, user_raw2can_map
        )
        state['scores'] = scores

        # 7. Add MATCHES_JOB edges to current graph (Speed: FAST)
        for job_node, score, explain in scores:
            G.add_edge(USER_ID, job_node, rel="MATCHES_JOB", score=round(score, 3))

        # Clean up
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
    if state.get('current_G') is None or state.get('cv_text') is None:
        return jsonify({'error': 'No graph available. Please upload a CV first.'}), 400

    try:
        G = state['current_G']
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
    """Bilingual Personalized AI Interview Endpoint"""
    if state.get('cv_text') is None:
        return jsonify({'reply': "I'm ready to interview you! Please upload your CV first so I can tailor the questions to your experience. (Tôi đã sẵn sàng phỏng vấn bạn! Vui lòng tải CV lên trước để tôi có thể điều chỉnh câu hỏi phù hợp với kinh nghiệm của bạn.)"})

    data = request.json
    user_msg = data.get('message', '').lower()
    history = data.get('history', [])
    
    # Context from state
    user_role = state.get('user_role_can', 'Professional')
    user_skills = list(state.get('user_prob', {}).keys())
    
    # Target Job (from top match)
    target_job = "the position"
    if state.get('scores') and len(state['scores']) > 0:
        target_job = state['job_info'][state['scores'][0][0]]['title']

    # Determine interview stage based on history length
    turn_count = len([h for h in history if h.get('role') == 'user'])
    
    # Bilingual rule-based logic
    if turn_count == 0:
        reply = (f"Hello! I am your AI Interviewer. Based on your profile, I see you have a strong background as a {user_role}. "
                 f"We are considering you for the {target_job} role. To start, could you please introduce yourself and highlight how your experience fits this position?\n\n"
                 f"(Chào bạn! Tôi là Người phỏng vấn AI. Dựa trên hồ sơ của bạn, tôi thấy bạn có nền tảng vững chắc là một {user_role}. "
                 f"Chúng tôi đang xem xét bạn cho vị trí {target_job}. Để bắt đầu, bạn vui lòng giới thiệu bản thân và nêu bật kinh nghiệm của bạn phù hợp với vị trí này như thế nào?)")
    
    elif turn_count == 1:
        if user_skills:
            skill = user_skills[0]
            reply = (f"That's a great overview. I noticed '{skill}' is one of your key skills. Can you describe a specific project where you applied this skill to solve a complex problem?\n\n"
                     f"(Đó là một phần giới thiệu tuyệt vời. Tôi nhận thấy '{skill}' là một trong những kỹ năng chính của bạn. Bạn có thể mô tả một dự án cụ thể mà bạn đã áp dụng kỹ năng này để giải quyết một vấn đề phức tạp không?)")
        else:
            reply = ("Thank you. Can you tell me about the most challenging technical project you've worked on recently?\n\n"
                     "(Cảm ơn bạn. Bạn có thể kể về dự án kỹ thuật thử thách nhất mà bạn đã thực hiện gần đây không?)")

    elif turn_count == 2:
        reply = (f"Interesting. Problem-solving is crucial for a {user_role}. Now, how do you typically handle tight deadlines or shifting priorities in a team environment?\n\n"
                 f"(Thật thú vị. Giải quyết vấn đề rất quan trọng đối với một {user_role}. Bây giờ, bạn thường xử lý thế nào khi gặp thời hạn gấp hoặc ưu tiên công việc thay đổi trong môi trường nhóm?)")
    
    elif turn_count == 3:
        reply = (f"I appreciate that perspective. Looking at the requirements for {target_job}, what do you consider to be your biggest area for growth or a skill you are currently looking to develop further?\n\n"
                 f"(Tôi đánh giá cao quan điểm đó. Nhìn vào các yêu cầu cho vị trí {target_job}, bạn coi đâu là lĩnh vực cần phát triển nhất hoặc kỹ năng nào bạn đang muốn hoàn thiện hơn?)")
    
    elif 'salary' in user_msg or 'expect' in user_msg or 'lương' in user_msg:
         reply = ("We can certainly discuss compensation later. For now, let's focus on your fit for the role. Do you have any questions for me about the company culture or the team?\n\n"
                  "(Chúng ta chắc chắn sẽ thảo luận về thù lao sau. Hiện tại, hãy tập trung vào mức độ phù hợp của bạn với vị trí này. Bạn có câu hỏi nào cho tôi về văn hóa công ty hoặc đội ngũ không?)")
    
    else:
        replies = [
            ("That's a very clear explanation. Thank you. (Đó là một lời giải thích rất rõ ràng. Cảm ơn bạn.)"),
            ("I see. That would certainly be valuable in this role. (Tôi hiểu rồi. Điều đó chắc chắn sẽ rất giá trị trong vai trò này.)"),
            ("Could you elaborate a bit more on how you handled the communication in that situation? (Bạn có thể nói rõ hơn một chút về cách bạn xử lý việc giao tiếp trong tình huống đó không?)"),
            ("Excellent. I have a good understanding of your background now. Do you have any final questions for me? (Tuyệt vời. Bây giờ tôi đã hiểu rõ về nền tảng của bạn. Bạn có câu hỏi cuối cùng nào cho tôi không?)")
        ]
        import random
        reply = random.choice(replies)

    import time
    time.sleep(1.0)
    
    return jsonify({'reply': reply})

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

@app.route('/api/search')
def api_search():
    """Real-time job search with advanced filtering"""
    query = request.args.get('q', '').lower()
    city = request.args.get('city', 'All Locations').lower()
    offset = int(request.args.get('offset', 0))
    limit = int(request.args.get('limit', 20))
    exp_levels = request.args.get('exp', '') # e.g. "intern,junior,senior,lead"
    job_types = request.args.get('type', '') # e.g. "full,part,remote"
    min_salary = int(request.args.get('min_salary', 0))
    
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
    
    return jsonify({
        'jobs': output,
        'has_more': (offset + limit) < total_count,
        'total': total_count
    })

if __name__ == '__main__':
    # Initialize system and preload DB
    try:
        excel_path = os.path.join(os.path.dirname(__file__), 'db_job_tuan.xlsx')
        if os.path.exists(excel_path):
            print("🚀 Initializing NCKH Job Matching System...")
            
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
            
            print("✅ System Ready.")
    except Exception as e:
        print(f"❌ Error during initialization: {e}")

    app.run(debug=True, host='0.0.0.0', port=5000)
