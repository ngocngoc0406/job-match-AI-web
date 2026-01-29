# -*- coding: utf-8 -*-
"""Skill extraction and matching functions"""

import re
from collections import defaultdict
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from text_processing import norm_text, split_cv_sections, _combine_probs, sid
from config import SKILL_LEXICON, SECTION_WEIGHT, MIN_KEEP_PROB, CORE_SKILLS_CANON
from text_processing import sid
def _compile_skill_patterns(lexicon: dict):
    """Compile skill pattern regexes"""
    comp = {}
    for canon, aliases in lexicon.items():
        pats = []
        for a in aliases:
            a_norm = norm_text(a)
            if " " in a_norm or "-" in a_norm:
                pats.append(rf"(?<!\w){re.escape(a_norm)}(?!\w)")
            else:
                pats.append(rf"\b{re.escape(a_norm)}\b")
        comp[canon] = re.compile("|".join(pats), flags=re.IGNORECASE)
    return comp

SKILL_PATTERNS = _compile_skill_patterns(SKILL_LEXICON)

# Build TF-IDF for skill matching
_skill_texts = []
_skill_to_canon = []
for canon, aliases in SKILL_LEXICON.items():
    _skill_texts.append(norm_text(canon))
    _skill_to_canon.append(canon)
    for a in aliases:
        _skill_texts.append(norm_text(a))
        _skill_to_canon.append(canon)

_skill_tfidf = TfidfVectorizer(analyzer='char_wb', ngram_range=(3,5), min_df=1)
_skill_X = _skill_tfidf.fit_transform(_skill_texts)

def best_canonical_match(phrase: str):
    """Find best canonical skill match using TF-IDF"""
    p = norm_text(phrase)
    if not p:
        return None, 0.0
    vp = _skill_tfidf.transform([p])
    sims = cosine_similarity(vp, _skill_X).ravel()
    if sims.size == 0:
        return None, 0.0
    best_idx = int(sims.argmax())
    best_score = float(sims[best_idx])
    best_canon = _skill_to_canon[best_idx]
    return best_canon, best_score

def extract_skills_probabilistic(text: str, min_keep=MIN_KEEP_PROB):
    """Extract skills with probabilistic scoring"""
    sections = split_cv_sections(text)
    skills_prob = {}
    raw_hits = defaultdict(list)

    for sec, chunk in sections.items():
        w_sec = SECTION_WEIGHT.get(sec, 0.25)
        chunk_norm = norm_text(chunk)

        for canon, pat in SKILL_PATTERNS.items():
            matches = list(pat.finditer(chunk_norm))
            if not matches:
                continue

            m = min(len(matches), 4)
            p_occ = 1 - (1 - w_sec) ** m
            if canon in CORE_SKILLS_CANON:
                p_occ = min(0.95, p_occ + 0.05)

            prev = skills_prob.get(canon, 0.0)
            skills_prob[canon] = _combine_probs([prev, p_occ])

            for mt in matches[:3]:
                span = chunk_norm[max(0, mt.start()-18): mt.end()+18]
                raw_hits[canon].append(("alias_hit", sec, span))

    skills_prob = {k: round(v, 3) for k, v in skills_prob.items() if v >= min_keep}
    return skills_prob, dict(raw_hits)

def weighted_skill_overlap_prob(user_prob: dict, job_prob: dict):
    """Calculate job-centric skill coverage"""
    if not job_prob:
        return 0.0, {"reason": "no_job_skill_signal", "top_skill_contrib": []}

    num = 0.0
    den = 0.0
    contrib = []

    for s, pj in job_prob.items():
        w = 2.0 if s in CORE_SKILLS_CANON else 1.0
        pu = float(user_prob.get(s, 0.0))
        num += min(pu, pj) * w
        den += pj * w
        if pu > 0:
            contrib.append((s, round(min(pu, pj) * w, 4), round(pu,3), round(pj,3), w))

    score = (num / den) if den > 0 else 0.0
    contrib.sort(key=lambda x: x[1], reverse=True)
    return float(round(score, 3)), {"top_skill_contrib": contrib[:10]}

def add_skillraw_nodes_and_links(G, owner_n, text, owner_rel_raw, fuzzy_threshold=0.78):
    """Add skill raw nodes and links to graph"""
    text_n = norm_text(text)
    raw2can_map = defaultdict(list)
    seen_raws = set()

    # Exact/alias matches
    for canon, pat in SKILL_PATTERNS.items():
        for m in pat.finditer(text_n):
            phrase = m.group(0)
            if phrase in seen_raws:
                continue

            raw_n = f"skillraw::{sid('raw', phrase)}"
            can_n = f"skill::{sid('skill', canon)}"

            G.add_node(raw_n, ntype="SkillRaw", label=phrase)
            G.add_node(can_n, ntype="Skill", label=canon)

            p = 0.70 if norm_text(phrase) == norm_text(canon) else 0.45
            G.add_edge(owner_n, raw_n, rel=owner_rel_raw)
            G.add_edge(raw_n, can_n, rel="NORMALIZES_TO", prob=round(p, 3))

            raw2can_map[phrase].append((canon, p))
            seen_raws.add(phrase)

    # Fuzzy matching
    words = [w for w in re.findall(r"\w+", text_n) if len(w) >= 3]
    tokens = set(words)
    tokens.update({f"{words[i]} {words[i+1]}" for i in range(len(words)-1)})

    for phrase in tokens:
        if phrase in seen_raws:
            continue

        canon, score = best_canonical_match(phrase)
        if canon and score >= fuzzy_threshold:
            raw_n = f"skillraw::{sid('raw', phrase)}"
            can_n = f"skill::{sid('skill', canon)}"

            G.add_node(raw_n, ntype="SkillRaw", label=phrase)
            G.add_node(can_n, ntype="Skill", label=canon)

            p = round(0.35 * float(score) + 0.15, 3)
            G.add_edge(owner_n, raw_n, rel=owner_rel_raw)
            G.add_edge(raw_n, can_n, rel="NORMALIZES_TO", prob=p)

            raw2can_map[phrase].append((canon, p))
            seen_raws.add(phrase)

    raw2can_best = {}
    for raw_phrase, vals in raw2can_map.items():
        for canon, p in vals:
            if canon not in raw2can_best or p > raw2can_best[canon][1]:
                raw2can_best[canon] = (raw_phrase, p)

    return raw2can_map, raw2can_best
