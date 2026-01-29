# -*- coding: utf-8 -*-
"""User-job matching and scoring functions"""

import numpy as np
from text_processing import norm_text, role_sim, exp_sim, location_match_score
from skill_extraction import extract_skills_probabilistic
from config import CORE_SKILLS_CANON, TOPK_USER_JOB, W_SKILL, W_LOC, SIM_THRESHOLD, CANDIDATES_TOP, TOPK_SIMILAR

def prob_skill_sim_job_job(Aprob: dict, Bprob: dict):
    """Calculate skill probability similarity between two jobs"""
    if not Aprob or not Bprob:
        return 0.0

    keys = set(Aprob.keys()) | set(Bprob.keys())
    num, den = 0.0, 0.0

    for s in keys:
        w = 2.0 if s in CORE_SKILLS_CANON else 1.0
        a = float(Aprob.get(s, 0.0))
        b = float(Bprob.get(s, 0.0))
        num += min(a, b) * w
        den += b * w

    return float(num / den) if den > 0 else 0.0

def text_sim_job_job(j1, j2, IDX, X):
    """Calculate text similarity between two jobs using TF-IDF"""
    if j1 not in IDX or j2 not in IDX:
        return 0.0
    i, j = IDX[j1], IDX[j2]
    return float(X[i].multiply(X[j]).sum())

def sim_score_job_job(j1, j2, job_info, IDX, X):
    """Calculate similarity score between two jobs (from collab.py logic)"""
    a, b = job_info[j1], job_info[j2]

    # Skill probability similarity
    s_skill = prob_skill_sim_job_job(a["prob_skills"], b["prob_skills"])
    
    # Text similarity
    s_text = text_sim_job_job(j1, j2, IDX, X)
    
    # Role similarity
    s_role = role_sim(a["role_can"], b["role_can"])
    
    # Experience similarity
    s_exp = exp_sim(a["exp_bucket"], b["exp_bucket"])
    
    # Location similarity
    s_loc = (
        1.0
        if norm_text(a["city"]) == norm_text(b["city"])
        and a["city"] != "Unknown"
        else 0.0
    )

    # Weights from collab.py
    W = {
        "skill": 0.40,
        "text":  0.35,
        "exp":   0.15,
        "loc":   0.10,
    }

    score = (
        W["skill"] * s_skill +
        W["text"]  * s_text  +
        W["exp"]   * s_exp   +
        W["loc"]   * s_loc
    )

    explain = {
        "skill": round(s_skill, 3),
        "text":  round(s_text, 3),
        "role":  round(s_role, 3),
        "exp":   round(s_exp, 3),
        "loc":   round(s_loc, 3),
    }

    return float(round(score, 3)), explain

def build_job_job_similar_edges(G, valid_job_nodes, job_info, IDX, X):
    """Build SIMILAR_TO edges between jobs based on similarity score (from collab.py logic)"""
    # Remove existing SIMILAR_TO edges
    edges_to_remove = [
        (u, v) for u, v, d in list(G.edges(data=True))
        if d.get("rel") == "SIMILAR_TO"
    ]
    G.remove_edges_from(edges_to_remove)

    sim_edge_count = 0

    for a_idx, j1 in enumerate(valid_job_nodes):
        if j1 not in IDX:
            continue
            
        v = X[a_idx]
        sims = (v @ X.T).toarray().ravel()
        sims[a_idx] = 0.0

        # Get top candidates
        if CANDIDATES_TOP < len(sims):
            cand_pos = np.argpartition(-sims, CANDIDATES_TOP)[:CANDIDATES_TOP]
        else:
            cand_pos = np.arange(len(sims))

        scored = []
        for b_pos in cand_pos:
            j2 = valid_job_nodes[b_pos]
            if j1 == j2 or j2 not in job_info:
                continue

            s, ex = sim_score_job_job(j1, j2, job_info, IDX, X)
            if s >= SIM_THRESHOLD:
                scored.append((j2, s, ex))

        scored.sort(key=lambda x: x[1], reverse=True)

        # Add top TOPK_SIMILAR edges
        for j2, s, ex in scored[:TOPK_SIMILAR]:
            G.add_edge(j1, j2, rel="SIMILAR_TO", score=s, explain=ex)
            G.add_edge(j2, j1, rel="SIMILAR_TO", score=s, explain=ex)
            sim_edge_count += 2

    return sim_edge_count

def explain_user_job(user_prob, job_prob, user_raw2can=None, job_raw2can=None):
    """Generate XAI explanation for user-job match"""
    if not job_prob:
        return {
            "components": {"skill_coverage": 0.0},
            "evidence": {"matched_skills": [], "missing_skills": []},
            "paths": []
        }

    num = 0.0
    den = 0.0
    matched = []
    missing = []

    for sk, pj in job_prob.items():
        w = 2.0 if sk in CORE_SKILLS_CANON else 1.0
        pu = float(user_prob.get(sk, 0.0))

        den += pj * w

        if pu > 0:
            contrib = min(pu, pj) * w
            num += contrib
            matched.append({
                "skill": sk,
                "user_prob": round(pu, 3),
                "job_prob": round(pj, 3),
                "weight": w,
                "contrib": round(contrib, 4)
            })
        else:
            missing.append({
                "skill": sk,
                "job_prob": round(pj, 3),
                "weight": w
            })

    coverage = num / den if den > 0 else 0.0

    matched.sort(key=lambda x: x["contrib"], reverse=True)
    missing.sort(key=lambda x: x["job_prob"] * x["weight"], reverse=True)

    paths = []
    for m in matched[:5]:
        sk = m['skill']
        raw_evidence = []
        
        if user_raw2can:
            for r, vals in user_raw2can.items():
                for canon, p in vals:
                    if canon == sk:
                        raw_evidence.append((r, p, 'user'))
        if job_raw2can:
            for r, vals in job_raw2can.items():
                for canon, p in vals:
                    if canon == sk:
                        raw_evidence.append((r, p, 'job'))

        raw_evidence.sort(key=lambda x: x[1], reverse=True)
        top_raw = raw_evidence[:2]

        if top_raw:
            for r, p, source in top_raw:
                if source == 'user':
                    paths.append(f"User → HAS_SKILL_RAW → SkillRaw('{r}') → NORMALIZES_TO({p}) → Skill('{sk}') → REQUIRES_SKILL → Job")
                else:
                    paths.append(f"Job → MENTIONS_SKILL_RAW → SkillRaw('{r}') → NORMALIZES_TO({p}) → Skill('{sk}') ← User")
        else:
            paths.append(f"User → HAS_SKILL → {sk} → REQUIRED_BY → Job")

    return {
        "components": {
            "skill_coverage": round(coverage, 3)
        },
        "evidence": {
            "matched_skills": matched,
            "missing_skills": missing
        },
        "paths": paths
    }

def user_job_score(user_prob, user_city, user_detail, job_node, job_info, 
                   IDX, X, cv_vec, tfidf, user_role_can, user_exp_bucket,
                   pseudo_text="", user_raw2can_best=None, user_raw2can_map=None):
    """Calculate user-job match score"""
    if job_node not in job_info:
        return 0.0, {"error": "job_not_in_job_info"}

    job = job_info[job_node]

    if user_raw2can_best:
        user_prob_max_raw = {
            canon: float(p)
            for canon, (_, p) in user_raw2can_best.items()
            if isinstance(p, (int, float))
        }
    else:
        user_prob_max_raw = user_prob

    xai = explain_user_job(user_prob_max_raw, job["prob_skills"], 
                          user_raw2can=user_raw2can_map, job_raw2can=job.get('raw2can'))
    s_skill = xai["components"]["skill_coverage"]
    ex_skill = xai["evidence"]

    i = IDX[job_node]
    if pseudo_text:
        from sklearn.preprocessing import normalize
        pseudo_vec = normalize(tfidf.transform([norm_text(pseudo_text)]))
        s_text = float((pseudo_vec @ X[i].T).sum())
    else:
        s_text = float((cv_vec @ X[i].T).sum())

    s_loc, ex_loc = location_match_score(
        user_city, user_detail,
        job["city"], job["detail"]
    )

    s_role = role_sim(user_role_can, job["role_can"])
    s_exp = exp_sim(user_exp_bucket, job["exp_bucket"])
    
    try:
        s_sal = 1.0 if job["sal_bucket"] != "Salary_Unknown" else 0.0
    except:
        s_sal = 0.0

    W = {
        'skill': 0.35,
        'text': 0.25,
        'location': 0.15,
        'role': 0.10,
        'exp': 0.10,
        'sal': 0.05,
    }

    score = (
        W['skill'] * s_skill +
        W['text'] * s_text +
        W['location'] * s_loc +
        W['role'] * s_role +
        W['exp'] * s_exp +
        W['sal'] * s_sal
    )

    explain = {
        "components": {
            "skill": round(s_skill, 3),
            "text": round(s_text, 3),
            "location": round(s_loc, 3),
            "role": round(s_role, 3),
            "experience": round(s_exp, 3),
            "salary": round(s_sal, 3),
        },
        "evidence": {
            "skill": ex_skill,
            "location": ex_loc,
        },
        "meta": {
            "user_city": user_city,
            "job_city": job["city"],
            "job_role": job["role_can"],
            "exp_bucket": job["exp_bucket"],
            "sal_bucket": job["sal_bucket"],
        }
    }

    return float(round(score, 3)), explain

def compute_user_job_scores(job_nodes, job_info, user_prob, user_city, user_detail,
                            IDX, X, cv_vec, tfidf, user_role_can, user_exp_bucket,
                            user_raw2can_best=None, user_raw2can_map=None):
    """Compute scores for all jobs"""
    scores = []
    valid_job_nodes = [j for j in job_nodes if j in job_info]

    for j in valid_job_nodes:
        sc, ex = user_job_score(
            user_prob, user_city, user_detail, j, job_info,
            IDX, X, cv_vec, tfidf, user_role_can, user_exp_bucket,
            user_raw2can_best=user_raw2can_best,
            user_raw2can_map=user_raw2can_map
        )
        scores.append((j, sc, ex))

    scores.sort(key=lambda x: x[1], reverse=True)
    return scores
