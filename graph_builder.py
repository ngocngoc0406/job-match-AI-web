
# -*- coding: utf-8 -*-
"""Graph building and user-job scoring functions"""

import networkx as nx
from rdflib import Graph as RDFGraph, Namespace, RDF, RDFS, OWL, Literal
from rdflib.namespace import XSD
from text_processing import (
    norm_text, sid, parse_location_city_detail, infer_role_canonical, 
    infer_role_raw, parse_year_range, exp_bucket, parse_salary, 
    salary_bucket_general
)
from skill_extraction import (
    extract_skills_probabilistic, add_skillraw_nodes_and_links, _combine_probs
)
from config import (
    CORE_SKILLS_CANON, RDF_CLASSES, RDF_OBJ_PROPS, 
    TOPK_USER_JOB
)
import random
def init_rdf_graph():
    """Initialize RDF graph"""
    rdf = RDFGraph()
    EX = Namespace("http://example.org/jobKG#")
    rdf.bind("ex", EX)

    for c in RDF_CLASSES:
        rdf.add((EX[c], RDF.type, OWL.Class))

    for p in RDF_OBJ_PROPS:
        rdf.add((EX[p], RDF.type, OWL.ObjectProperty))
    
    rdf.add((EX.SIMILAR_TO, RDF.type, OWL.SymmetricProperty))
    rdf.add((EX.score, RDF.type, OWL.DatatypeProperty))
    rdf.add((EX.score, RDFS.range, XSD.float))
    rdf.add((EX.prob, RDF.type, OWL.DatatypeProperty))
    rdf.add((EX.prob, RDFS.range, XSD.float))
    rdf.add((EX.confidence, RDF.type, OWL.DatatypeProperty))
    rdf.add((EX.confidence, RDFS.range, XSD.float))

    return rdf, EX

def _iri(ex_ns: Namespace, raw_id: str):
    """Sanitize graph identifiers for RDF URIs."""
    return ex_ns[str(raw_id).replace('::', '_').replace('-', '_')]


def add_node(G: nx.DiGraph, nx_id: str, ntype: str, label, rdf=None, ex_ns=None, **props):
    """Add a node to a NetworkX graph and optionally mirror it to RDF."""
    if not G.has_node(nx_id):
        G.add_node(nx_id, ntype=ntype, label=str(label), **props)

        if rdf is not None and ex_ns is not None:
            rdf.add((_iri(ex_ns, nx_id), RDF.type, ex_ns[ntype]))


def add_edge(G: nx.DiGraph, u: str, v: str, rel: str, rdf=None, ex_ns=None, **props):
    """Add an edge to a NetworkX graph and optionally mirror it to RDF."""
    G.add_edge(u, v, rel=rel, **props)

    if rdf is not None and ex_ns is not None:
        if rel in RDF_OBJ_PROPS:
            rdf.add((_iri(ex_ns, u), ex_ns[rel], _iri(ex_ns, v)))

        if 'prob' in props:
            rdf.add((_iri(ex_ns, u), ex_ns.prob, Literal(props['prob'], datatype=XSD.float)))
        if 'score' in props:
            rdf.add((_iri(ex_ns, u), ex_ns.score, Literal(props['score'], datatype=XSD.float)))

def build_user_node(G, cv_text):
    """Build user node from CV"""
    USER_ID = "user::cv_001"
    G.add_node(USER_ID, ntype="User", label="CV_User_001")

    user_prob_raw, user_hits = extract_skills_probabilistic(cv_text)
    user_city, user_detail = parse_location_city_detail(cv_text)

    user_raw2can_map, user_raw2can_best = add_skillraw_nodes_and_links(
        G, USER_ID, cv_text, owner_rel_raw="HAS_SKILL_RAW"
    )

    p_from_raw_user = {}
    if user_raw2can_map:
        for r, vals in user_raw2can_map.items():
            for c, p in vals:
                if c not in p_from_raw_user:
                    p_from_raw_user[c] = []
                p_from_raw_user[c].append(p)
        p_from_raw_user = {k: _combine_probs(vs) for k, vs in p_from_raw_user.items()}

    user_prob = dict(user_prob_raw)
    for sk, p_raw in p_from_raw_user.items():
        prev = user_prob.get(sk, 0.0)
        user_prob[sk] = round(_combine_probs([prev, p_raw]), 3)

    for sk, p in user_prob.items():
        sk_n = f"skill::{sid('skill', sk)}"
        G.add_node(sk_n, ntype="Skill", label=sk)
        G.add_edge(USER_ID, sk_n, rel="HAS_SKILL", prob=round(p, 3))

    u_loc_n = f"loc::{sid('loc', user_city)}"
    G.add_node(u_loc_n, ntype="Location", label=user_city)
    G.add_edge(USER_ID, u_loc_n, rel="LOCATED_IN", level="city")
    
    return USER_ID, user_prob, user_city, user_detail, user_raw2can_map, user_raw2can_best

def build_job_nodes(G, df, job_info=None, rdf=None, ex_ns=None):
    """Build job nodes in the graph (and optionally RDF graph)."""
    job_nodes = []
    job_info = job_info or {}

    for _, r in df.iterrows():
        jid = r["job_id"]
        title = r["job_title"]
        company = r["company"]

        job_n = f"job::{sid('job', jid)}"
        job_nodes.append(job_n)

        role_can = infer_role_canonical(title)
        role_raw = infer_role_raw(title)

        role_can_n = f"role_can::{sid('role_can', role_can)}"
        role_raw_n = f"role_raw::{sid('role_raw', role_raw)}"
        comp_n = f"company::{sid('company', company)}"

        add_node(G, job_n, "JobPosting", title, rdf=rdf, ex_ns=ex_ns, job_id=str(jid), url=str(r["job_url"]))
        add_node(G, role_can_n, "JobRoleCanonical", role_can, rdf=rdf, ex_ns=ex_ns)
        add_node(G, role_raw_n, "JobRoleRaw", role_raw, rdf=rdf, ex_ns=ex_ns)
        add_node(G, comp_n, "Company", company, rdf=rdf, ex_ns=ex_ns)

        add_edge(G, job_n, role_can_n, "HAS_ROLE_CANONICAL", rdf=rdf, ex_ns=ex_ns)
        add_edge(G, job_n, role_raw_n, "HAS_ROLE_RAW", rdf=rdf, ex_ns=ex_ns)
        add_edge(G, job_n, comp_n, "POSTED_BY", rdf=rdf, ex_ns=ex_ns)

        city, detail = parse_location_city_detail(f"{r['location']} {r['location_detail']}")
        loc_city_n = f"loc::{sid('loc', city)}"
        add_node(G, loc_city_n, "Location", city, rdf=rdf, ex_ns=ex_ns)
        add_edge(G, job_n, loc_city_n, "LOCATED_IN", rdf=rdf, ex_ns=ex_ns)

        e_min, e_max, _ = parse_year_range(r["experience"])
        exp_b = exp_bucket(e_min, e_max)
        exp_n = f"exp_bucket::{sid('exp', exp_b)}"
        add_node(G, exp_n, "ExperienceBucket", exp_b, rdf=rdf, ex_ns=ex_ns)
        add_edge(G, job_n, exp_n, "REQUIRES_EXP_BUCKET", rdf=rdf, ex_ns=ex_ns)

        s_min, s_max, cur, nego = parse_salary(r["salary"])
        sal_b = salary_bucket_general(s_min, s_max, cur, nego)
        sal_n = f"sal_bucket::{sid('sal', sal_b)}"
        add_node(G, sal_n, "SalaryBucket", sal_b, rdf=rdf, ex_ns=ex_ns)
        add_edge(G, job_n, sal_n, "HAS_SALARY_BUCKET", rdf=rdf, ex_ns=ex_ns)

        job_text_full = f"{r['requirements']} {r['job_desc']} {r['benefit']}"
        job_prob_raw, _ = extract_skills_probabilistic(job_text_full)

        raw2can_map, raw2can_best = add_skillraw_nodes_and_links(
            G, job_n, job_text_full, owner_rel_raw="REQUIRES_SKILL_RAW"
        )

        p_from_raw = {}
        if raw2can_map:
            for raw_phrase, vals in raw2can_map.items():
                for canon, p in vals:
                    p_from_raw.setdefault(canon, []).append(p)
            p_from_raw = {k: _combine_probs(vs) for k, vs in p_from_raw.items()}

        job_prob = dict(job_prob_raw)
        for sk, p_raw in p_from_raw.items():
            prev = job_prob.get(sk, 0.0)
            job_prob[sk] = round(_combine_probs([prev, p_raw]), 3)

        for sk, p in job_prob.items():
            sk_n = f"skill::{sid('skill', sk)}"
            add_node(G, sk_n, "Skill", sk, rdf=rdf, ex_ns=ex_ns)
            add_edge(G, job_n, sk_n, "REQUIRES_SKILL", rdf=rdf, ex_ns=ex_ns, prob=p)

        job_info[job_n] = {
            "title": title,
            "company": company,
            "url": str(r["job_url"]),
            "role_can": role_can,
            "exp_bucket": exp_b,
            "sal_bucket": sal_b,
            "city": city,
            "detail": detail,
            "prob_skills_raw": job_prob_raw,
            "prob_skills": job_prob,
            "raw2can": raw2can_map,
            "raw2can_best": raw2can_best,
            "text": norm_text(
                f"{r['job_title']} {r['requirements']} "
                f"{r['job_desc']} {r['benefit']} {r['job_type']}"
            )
        }

    return job_nodes, job_info

# def build_user_node(G, cv_text, rdf=None, ex_ns=None):
#     """Build user node from CV (and optionally RDF graph)."""
#     USER_ID = "user::cv_001"
#     add_node(G, USER_ID, "User", "CV_User_001", rdf=rdf, ex_ns=ex_ns)

#     user_prob_raw, user_hits = extract_skills_probabilistic(cv_text)
#     user_city, user_detail = parse_location_city_detail(cv_text)

#     user_raw2can_map, user_raw2can_best = add_skillraw_nodes_and_links(
#         G, USER_ID, cv_text, owner_rel_raw="HAS_SKILL_RAW"
#     )

#     p_from_raw_user = {}
#     if user_raw2can_map:
#         for r, vals in user_raw2can_map.items():
#             for c, p in vals:
#                 if c not in p_from_raw_user:
#                     p_from_raw_user[c] = []
#                 p_from_raw_user[c].append(p)
#         p_from_raw_user = {k: _combine_probs(vs) for k, vs in p_from_raw_user.items()}

#     user_prob = dict(user_prob_raw)
#     for sk, p_raw in p_from_raw_user.items():
#         prev = user_prob.get(sk, 0.0)
#         user_prob[sk] = round(_combine_probs([prev, p_raw]), 3)

#     for sk, p in user_prob.items():
#         sk_n = f"skill::{sid('skill', sk)}"
#         add_node(G, sk_n, "Skill", sk, rdf=rdf, ex_ns=ex_ns)
#         add_edge(G, USER_ID, sk_n, "HAS_SKILL", rdf=rdf, ex_ns=ex_ns, prob=round(p, 3))

#     u_loc_n = f"loc::{sid('loc', user_city)}"
#     add_node(G, u_loc_n, "Location", user_city, rdf=rdf, ex_ns=ex_ns)
#     add_edge(G, USER_ID, u_loc_n, "LOCATED_IN", rdf=rdf, ex_ns=ex_ns, level="city")

#     return USER_ID, user_prob, user_city, user_detail, user_raw2can_map, user_raw2can_best

def build_strict_user_job_graph(G, user_node, topk=3):
    """Build a focused subgraph containing user, top-k jobs, and their attributes."""
    keep = {user_node}

    # Get top-k jobs
    jobs = [
        v for u, v, d in G.edges(data=True)
        if u == user_node and d.get("rel") == "MATCHES_JOB"
    ]
    jobs = sorted(
        jobs,
        key=lambda j: G.edges[user_node, j].get("score", 0),
        reverse=True
    )[:topk]

    keep.update(jobs)

    # Add user's attributes
    for _, v, d in G.edges(user_node, data=True):
        if d.get("rel") in ["HAS_SKILL", "LOCATED_IN"]:
            keep.add(v)

    # Add job attributes
    for j in jobs:
        for _, v, d in G.edges(j, data=True):
            if d.get("rel") in [
                "REQUIRES_SKILL",
                "LOCATED_IN",
                "HAS_SALARY_BUCKET",
                "REQUIRES_EXP_BUCKET",
                "HAS_ROLE_CANONICAL",
                "POSTED_BY"
            ]:
                keep.add(v)

    # Add SIMILAR_TO relationships between jobs
    for i, j1 in enumerate(jobs):
        for j2 in jobs[i+1:]:
            if G.has_edge(j1, j2):
                pass  # Already included in subgraph edges
            elif G.has_edge(j2, j1):
                pass  # Already included in subgraph edges

    return G.subgraph(keep).copy()


    # if t == "Skill":
    #     return 1150
    # return 1700
def find_job_node_by_id(G, val):
    if val is None:
        return None

    node = f"job::{sid('job', val)}"
    if G.has_node(node):
        return node

    val_str = str(val)
    for n in G.nodes:
        if G.nodes[n].get("job_id") == val_str:
            return n
    return None

def find_job_node_random(job_nodes, seed=42):
    rnd = random.Random(seed)
    return rnd.choice(job_nodes) if job_nodes else None
def pick_center_node(
    G,
    USER_ID,
    CENTER_MODE,
    scores,
    job_nodes,
    CENTER_JOB_ID=None,
    RANDOM_SEED=42
):
    if CENTER_MODE == "user":
        return USER_ID

    if CENTER_MODE == "top_job":
        return scores[0][0] if scores else job_nodes[0]

    if CENTER_MODE == "job_id":
        return (
            find_job_node_by_id(G, CENTER_JOB_ID)
            or (scores[0][0] if scores else job_nodes[0])
        )

    if CENTER_MODE == "random_job":
        return (
            find_job_node_random(job_nodes, RANDOM_SEED)
            or (scores[0][0] if scores else job_nodes[0])
        )

    return USER_ID
