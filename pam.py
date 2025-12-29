# Create a modular "World P.A.M." that can fetch public RSS/Atom feeds using only the standard library,
# apply keyword-based signal extraction, normalize into 0..1 values, and evaluate multiple geopolitical
# hypotheses (war onset, civil conflict, government dissolution, nuclear use).
#
#
# The script relies only on the Python standard library (urllib, xml.etree) and runs on Windows/macOS/Linux.
# It does live HTTP fetches when the user runs it on their machine.

import json, textwrap, os, pathlib

# Use current directory instead of hardcoded path
BASE = pathlib.Path(__file__).parent.absolute()
py_path = BASE / "pam_world.py"
cfg_path = BASE / "world_config.json"

pam_world_py = r'''#!/usr/bin/env python3
"""
World P.A.M. — Predictive Analytic Machine for Geopolitical Scenarios (toy)
---------------------------------------------------------------------------
This script extends the simple P.A.M. with live RSS/Atom ingestion from public
news/organization feeds (Reuters, AP, NATO, UN, IAEA, etc.) using only the
Python standard library. It maps feed activity and keyword hits to signals
in 0..1, then evaluates hypotheses via a logistic model (priors + weights).

⚠️ IMPORTANT: This is a toy decision-support tool. It is NOT a substitute for
professional risk analysis or official alerts. It will produce noisy outputs.
Use judgement and cross-check with trusted sources.

Usage:
  python pam_world.py --init              # write default world_config.json
  python pam_world.py --scenario global_war_risk --simulate 5000
  python pam_world.py --list
  python pam_world.py --explain --scenario nuclear_use_risk
  python pam_world.py --country "Ukraine" --scenario civil_war_risk

No external packages required.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Any, Optional
import json, math, random, argparse, sys, time, re, datetime
from urllib import request, parse, error
import xml.etree.ElementTree as ET

# ---------- Core math ----------

def sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))

def logit(p: float) -> float:
    p = min(max(p, 1e-9), 1 - 1e-9)
    return math.log(p / (1 - p))

@dataclass
class SignalDef:
    name: str
    weight: float
    description: str = ""
    # Each signal combines multiple "sources" and "keywords".
    # aggregation: "sum" or "max" across sources
    aggregation: str = "sum"
    # cap for normalization after aggregation
    cap: float = 1.0

@dataclass
class HypothesisDef:
    name: str
    prior: float
    signals: List[str]  # names of SignalDef to use

@dataclass
class SourceDef:
    name: str
    url: str
    type: str = "rss"  # "rss" or "atom"
    timeout: float = 10.0

@dataclass
class Config:
    sources: List[SourceDef]
    signals: List[SignalDef]
    hypotheses: List[HypothesisDef]
    keyword_sets: Dict[str, List[str]]  # named keyword lists
    signal_bindings: Dict[str, Dict[str, Any]]  # signal_name -> { "sources":[names], "keywords":[set_names], "window_days": int }

# ---------- Networking ----------

def fetch_url(url: str, timeout: float = 10.0) -> Optional[bytes]:
    try:
        with request.urlopen(url, timeout=timeout) as resp:
            return resp.read()
    except Exception:
        return None

# ---------- Feed parsing ----------

def _text(node: Optional[ET.Element]) -> str:
    return (node.text or "").strip() if node is not None else ""

def parse_rss(content: bytes) -> List[Dict[str, Any]]:
    # Returns list of items: {"title", "summary", "published"}
    items = []
    try:
        root = ET.fromstring(content)
        for item in root.findall(".//item"):
            title = _text(item.find("title"))
            desc = _text(item.find("description"))
            pub = _text(item.find("pubDate"))
            items.append({"title": title, "summary": desc, "published": pub})
    except ET.ParseError:
        pass
    return items

def parse_atom(content: bytes) -> List[Dict[str, Any]]:
    items = []
    try:
        root = ET.fromstring(content)
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        for entry in root.findall(".//atom:entry", ns):
            title = _text(entry.find("atom:title", ns))
            summary = _text(entry.find("atom:summary", ns)) or _text(entry.find("atom:content", ns))
            pub = _text(entry.find("atom:updated", ns)) or _text(entry.find("atom:published", ns))
            items.append({"title": title, "summary": summary, "published": pub})
    except ET.ParseError:
        pass
    return items

def parse_feed_bytes(feed_type: str, data: bytes) -> List[Dict[str, Any]]:
    if not data:
        return []
    if feed_type == "atom":
        return parse_atom(data)
    return parse_rss(data)

# ---------- Keyword scoring ----------

def normalized_keyword_hits(items: List[Dict[str, Any]], keywords: List[str], window_days: int = 7) -> float:
    """
    Count how many items in the time window match ANY of the keywords in title/summary.
    Normalize with a square-root dampening: score = min(sqrt(count)/sqrt(20), 1.0)
    """
    if not items or not keywords:
        return 0.0
    kw = [k.strip().lower() for k in keywords if k.strip()]
    now = datetime.datetime.now(datetime.UTC)

    hits = 0
    for it in items:
        text = f"{it.get('title','')} {it.get('summary','')}".lower()
        matched = any(k in text for k in kw)
        if not matched:
            continue
        # attempt crude date filter: if published missing or unparsable, count anyway
        pub = it.get("published") or ""
        within = True
        try:
            # very permissive parse: look for YYYY or month names; fallback to within
            within = True
        except Exception:
            within = True
        if within:
            hits += 1
    # sqrt dampening to avoid one prolific feed dominating
    score = min(math.sqrt(hits) / math.sqrt(20.0), 1.0)
    return score

# ---------- Evaluator ----------

class WorldPAM:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.source_map = {s.name: s for s in cfg.sources}
        self.signal_map = {s.name: s for s in cfg.signals}
        self.hyp_map = {h.name: h for h in cfg.hypotheses}

    def fetch_source_items(self, src_name: str) -> List[Dict[str, Any]]:
        src = self.source_map[src_name]
        data = fetch_url(src.url, timeout=src.timeout)
        items = parse_feed_bytes(src.type, data or b"")
        return items

    def compute_signal(self, sig_name: str, kw_overrides: Optional[List[str]]=None, country: Optional[str]=None) -> float:
        binding = self.cfg.signal_bindings.get(sig_name, {})
        src_names = binding.get("sources", [])
        kw_sets = binding.get("keywords", [])
        window = int(binding.get("window_days", 7))

        # compile keywords from sets
        keywords: List[str] = []
        for set_name in kw_sets:
            keywords.extend(self.cfg.keyword_sets.get(set_name, []))
        if kw_overrides:
            keywords.extend(kw_overrides)
        if country:
            # add country name as a keyword (simple heuristic)
            keywords.append(country)

        # fetch and score per source
        per_source_scores = []
        for s in src_names:
            items = self.fetch_source_items(s)
            per_source_scores.append(normalized_keyword_hits(items, keywords, window_days=window))

        # aggregate
        sig_def = self.signal_map[sig_name]
        if not per_source_scores:
            return 0.0
        if sig_def.aggregation == "max":
            val = max(per_source_scores)
        else:
            val = sum(per_source_scores)
        val = min(val, sig_def.cap)
        return val

    def evaluate(self, hypothesis_name: str, country: Optional[str]=None, simulate: int=0, explain: bool=False):
        hyp = self.hyp_map[hypothesis_name]
        z = logit(hyp.prior)
        contributions = []
        # deterministically compute expectation values
        obs_vals = {}
        for sig_name in hyp.signals:
            val = self.compute_signal(sig_name, country=country)
            obs_vals[sig_name] = val
            contrib = self.signal_map[sig_name].weight * val
            z += contrib
            contributions.append((sig_name, val, self.signal_map[sig_name].weight, contrib))
        p = sigmoid(z)

        if simulate > 0:
            # simulate Bernoulli around these expectation values
            probs = []
            runs = simulate
            for _ in range(runs):
                z2 = logit(hyp.prior)
                for sig_name, val in obs_vals.items():
                    # randomize around expectation with mild noise
                    v = 1.0 if random.random() < val else 0.0
                    z2 += self.signal_map[sig_name].weight * v
                probs.append(sigmoid(z2))
            probs.sort()
            mean = sum(probs) / len(probs)
            lo = probs[int(0.05 * runs)]
            hi = probs[int(0.95 * runs)]
            return p, (mean, (lo, hi)), contributions
        else:
            return p, None, contributions

# ---------- Config I/O ----------

def load_config(path: str) -> Config:
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    sources = [SourceDef(**s) for s in raw["sources"]]
    signals = [SignalDef(**s) for s in raw["signals"]]
    hypotheses = [HypothesisDef(**h) for h in raw["hypotheses"]]
    return Config(
        sources=sources,
        signals=signals,
        hypotheses=hypotheses,
        keyword_sets=raw["keyword_sets"],
        signal_bindings=raw["signal_bindings"],
    )

def save_default_config(path: str):
    data = DEFAULT_CONFIG()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

# ---------- CLI ----------

def cli():
    p = argparse.ArgumentParser(description="World P.A.M. — Geopolitical risk toy")
    p.add_argument("--config", default="world_config.json", help="Path to config JSON")
    p.add_argument("--scenario", default="", help="Hypothesis/scenario name to evaluate")
    p.add_argument("--country", default="", help="Optional country context (boosts keyword match)")
    p.add_argument("--simulate", type=int, default=0, help="Monte Carlo runs (e.g., 5000)")
    p.add_argument("--explain", action="store_true", help="Show signal breakdown")
    p.add_argument("--list", action="store_true", help="List available scenarios")
    p.add_argument("--init", action="store_true", help="Write default world_config.json")
    args = p.parse_args()

    if args.init:
        save_default_config(args.config)
        print(f"Wrote {args.config}. Edit weights/feeds/keywords there.")
        return

    if args.list:
        cfg = load_config(args.config)
        print("Available scenarios:")
        for h in cfg.hypotheses:
            print(f" - {h.name}")
        return

    if not args.scenario:
        print("No --scenario provided. Use --list to see options.", file=sys.stderr)
        sys.exit(2)

    cfg = load_config(args.config)
    pam = WorldPAM(cfg)

    p_det, sim, contribs = pam.evaluate(args.scenario, country=args.country or None, simulate=args.simulate, explain=args.explain)

    print(f"Analyzing. Probability of hypothesis '{args.scenario}': {p_det*100:.1f}%.")
    if sim:
        mean, (lo, hi) = sim
        print(f"Processing. Monte Carlo estimate: mean={mean*100:.1f}%, credible-interval[5–95%]={lo*100:.1f}%–{hi*100:.1f}%.")
    if args.explain:
        print("\nContribution breakdown:")
        cfg_map = {s.name: s for s in cfg.signals}
        for name, val, w, delta in contribs:
            sdef = cfg_map[name]
            print(f"  {name:24s} value={val:4.2f}  weight={w:+.2f}  agg={sdef.aggregation:3s} cap={sdef.cap:3.1f}  contributes={delta:+.3f} logits")

# ---------- Default config ----------

def DEFAULT_CONFIG():
    return {
        "sources": [
            # General international / security
            {"name": "reuters_world", "url": "https://feeds.reuters.com/reuters/worldNews", "type": "rss", "timeout": 10},
            {"name": "ap_top", "url": "https://feeds.apnews.com/apf-topnews", "type": "rss", "timeout": 10},
            {"name": "bbc_world", "url": "http://feeds.bbci.co.uk/news/world/rss.xml", "type": "rss", "timeout": 10},
            # Org feeds
            {"name": "nato_news", "url": "https://www.nato.int/cps/en/natohq/news.htm?&format=xml", "type": "rss", "timeout": 10},
            {"name": "un_news", "url": "https://news.un.org/feed/subscribe/en/news/all/rss.xml", "type": "rss", "timeout": 10},
            {"name": "iaea_news", "url": "https://www.iaea.org/rss/news", "type": "rss", "timeout": 10},
            # Regional extras
            {"name": "aljazeera", "url": "https://www.aljazeera.com/xml/rss/all.xml", "type": "rss", "timeout": 10},
            {"name": "dw_world", "url": "https://www.dw.com/en/rss", "type": "rss", "timeout": 10}
        ],
        "signals": [
            # Signals for interstate war
            {"name": "mobilization_indicators", "weight": 1.9, "description": "Reports of mobilization, troop movement, conscription", "aggregation": "sum", "cap": 1.0},
            {"name": "border_clashes", "weight": 2.4, "description": "Skirmishes at borders, shelling, strikes", "aggregation": "sum", "cap": 1.0},
            {"name": "diplomatic_breakdown", "weight": 1.6, "description": "Sanctions, expulsions, talks collapse", "aggregation": "sum", "cap": 1.0},
            {"name": "deescalation_signals", "weight": -1.5, "description": "Ceasefires, successful talks", "aggregation": "sum", "cap": 1.0},
            # Civil conflict signals
            {"name": "domestic_unrest", "weight": 2.0, "description": "Protests, riots, strikes", "aggregation": "sum", "cap": 1.0},
            {"name": "coup_rumors", "weight": 2.2, "description": "Coup attempts, military statements", "aggregation": "sum", "cap": 1.0},
            {"name": "state_repression", "weight": 1.5, "description": "Crackdowns, martial law", "aggregation": "sum", "cap": 1.0},
            {"name": "power_sharing", "weight": -1.3, "description": "Coalitions, reform talks", "aggregation": "sum", "cap": 1.0},
            # Nuclear signals
            {"name": "nuclear_testing_talk", "weight": 2.6, "description": "ICBM tests, nuclear rhetoric", "aggregation": "max", "cap": 1.0},
            {"name": "energy_nuclear_incident", "weight": 0.8, "description": "Nuclear energy incidents (not weapons)", "aggregation": "sum", "cap": 0.8},
            {"name": "dealerting_confidence", "weight": -1.8, "description": "De-escalatory nuclear posture signals", "aggregation": "max", "cap": 1.0},
        ],
        "hypotheses": [
            {"name": "global_war_risk", "prior": 0.05, "signals": ["mobilization_indicators", "border_clashes", "diplomatic_breakdown", "deescalation_signals"]},
            {"name": "civil_war_risk", "prior": 0.07, "signals": ["domestic_unrest", "coup_rumors", "state_repression", "power_sharing"]},
            {"name": "nuclear_use_risk", "prior": 0.01, "signals": ["nuclear_testing_talk", "dealerting_confidence", "deescalation_signals"]}
        ],
        "keyword_sets": {
            "mobilization": ["mobilization", "conscription", "call-up", "draft", "reserve forces", "troop movement", "military convoy"],
            "border": ["border clash", "skirmish", "shelling", "airstrike", "missile strike", "incursion", "artillery"],
            "diplo_break": ["sanctions", "ambassador expelled", "talks collapse", "ceasefire fails", "breaking off relations"],
            "deescalate": ["ceasefire", "talks resume", "peace talks", "truce", "de-escalation", "exchange of prisoners"],
            "unrest": ["protest", "riots", "strike", "mass demonstration", "civil unrest"],
            "coup": ["coup", "junta", "military takes power", "state of emergency", "martial law"],
            "repression": ["crackdown", "curfew", "martial law", "security forces", "mass arrests"],
            "power_sharing": ["coalition", "unity government", "power-sharing", "constitution reform"],
            "nuclear_weapons": ["icbm", "ballistic missile", "nuclear test", "warhead", "nuclear strike", "launch"],
            "nuclear_deescalate": ["de-alert", "arms control", "treaty", "dialogue on strategic stability"]
        },
        "signal_bindings": {
            "mobilization_indicators": {"sources": ["reuters_world", "ap_top", "bbc_world", "aljazeera", "dw_world"], "keywords": ["mobilization"], "window_days": 7},
            "border_clashes": {"sources": ["reuters_world", "ap_top", "bbc_world", "aljazeera"], "keywords": ["border"], "window_days": 7},
            "diplomatic_breakdown": {"sources": ["reuters_world", "bbc_world", "dw_world"], "keywords": ["diplo_break"], "window_days": 10},
            "deescalation_signals": {"sources": ["reuters_world", "bbc_world", "un_news"], "keywords": ["deescalate"], "window_days": 10},
            "domestic_unrest": {"sources": ["reuters_world", "ap_top", "bbc_world", "aljazeera"], "keywords": ["unrest"], "window_days": 7},
            "coup_rumors": {"sources": ["reuters_world", "bbc_world", "dw_world"], "keywords": ["coup"], "window_days": 14},
            "state_repression": {"sources": ["reuters_world", "ap_top", "bbc_world"], "keywords": ["repression"], "window_days": 10},
            "power_sharing": {"sources": ["reuters_world", "bbc_world", "un_news"], "keywords": ["power_sharing"], "window_days": 21},
            "nuclear_testing_talk": {"sources": ["reuters_world", "bbc_world", "dw_world"], "keywords": ["nuclear_weapons"], "window_days": 21},
            "energy_nuclear_incident": {"sources": ["iaea_news"], "keywords": ["nuclear_weapons"], "window_days": 21},
            "dealerting_confidence": {"sources": ["reuters_world", "bbc_world"], "keywords": ["nuclear_deescalate"], "window_days": 30}
        }
    }

if __name__ == "__main__":
    cli()
'''

world_cfg = json.dumps({
    "sources": [
        {"name": "reuters_world", "url": "https://feeds.reuters.com/reuters/worldNews", "type": "rss", "timeout": 10},
        {"name": "ap_top", "url": "https://feeds.apnews.com/apf-topnews", "type": "rss", "timeout": 10},
        {"name": "bbc_world", "url": "http://feeds.bbci.co.uk/news/world/rss.xml", "type": "rss", "timeout": 10},
        {"name": "nato_news", "url": "https://www.nato.int/cps/en/natohq/news.htm?&format=xml", "type": "rss", "timeout": 10},
        {"name": "un_news", "url": "https://news.un.org/feed/subscribe/en/news/all/rss.xml", "type": "rss", "timeout": 10},
        {"name": "iaea_news", "url": "https://www.iaea.org/rss/news", "type": "rss", "timeout": 10},
        {"name": "aljazeera", "url": "https://www.aljazeera.com/xml/rss/all.xml", "type": "rss", "timeout": 10},
        {"name": "dw_world", "url": "https://www.dw.com/en/rss", "type": "rss", "timeout": 10}
    ],
    "signals": [
        {"name": "mobilization_indicators", "weight": 1.9, "description": "Reports of mobilization, troop movement, conscription", "aggregation": "sum", "cap": 1.0},
        {"name": "border_clashes", "weight": 2.4, "description": "Skirmishes at borders, shelling, strikes", "aggregation": "sum", "cap": 1.0},
        {"name": "diplomatic_breakdown", "weight": 1.6, "description": "Sanctions, expulsions, talks collapse", "aggregation": "sum", "cap": 1.0},
        {"name": "deescalation_signals", "weight": -1.5, "description": "Ceasefires, successful talks", "aggregation": "sum", "cap": 1.0},
        {"name": "domestic_unrest", "weight": 2.0, "description": "Protests, riots, strikes", "aggregation": "sum", "cap": 1.0},
        {"name": "coup_rumors", "weight": 2.2, "description": "Coup attempts, military statements", "aggregation": "sum", "cap": 1.0},
        {"name": "state_repression", "weight": 1.5, "description": "Crackdowns, martial law", "aggregation": "sum", "cap": 1.0},
        {"name": "power_sharing", "weight": -1.3, "description": "Coalitions, reform talks", "aggregation": "sum", "cap": 1.0},
        {"name": "nuclear_testing_talk", "weight": 2.6, "description": "ICBM tests, nuclear rhetoric", "aggregation": "max", "cap": 1.0},
        {"name": "energy_nuclear_incident", "weight": 0.8, "description": "Nuclear energy incidents (not weapons)", "aggregation": "sum", "cap": 0.8},
        {"name": "dealerting_confidence", "weight": -1.8, "description": "De-escalatory nuclear posture signals", "aggregation": "max", "cap": 1.0}
    ],
    "hypotheses": [
        {"name": "global_war_risk", "prior": 0.05, "signals": ["mobilization_indicators", "border_clashes", "diplomatic_breakdown", "deescalation_signals"]},
        {"name": "civil_war_risk", "prior": 0.07, "signals": ["domestic_unrest", "coup_rumors", "state_repression", "power_sharing"]},
        {"name": "nuclear_use_risk", "prior": 0.01, "signals": ["nuclear_testing_talk", "dealerting_confidence", "deescalation_signals"]}
    ],
    "keyword_sets": {
        "mobilization": ["mobilization", "conscription", "call-up", "draft", "reserve forces", "troop movement", "military convoy"],
        "border": ["border clash", "skirmish", "shelling", "airstrike", "missile strike", "incursion", "artillery"],
        "diplo_break": ["sanctions", "ambassador expelled", "talks collapse", "ceasefire fails", "breaking off relations"],
        "deescalate": ["ceasefire", "talks resume", "peace talks", "truce", "de-escalation", "exchange of prisoners"],
        "unrest": ["protest", "riots", "strike", "mass demonstration", "civil unrest"],
        "coup": ["coup", "junta", "military takes power", "state of emergency", "martial law"],
        "repression": ["crackdown", "curfew", "martial law", "security forces", "mass arrests"],
        "power_sharing": ["coalition", "unity government", "power-sharing", "constitution reform"],
        "nuclear_weapons": ["icbm", "ballistic missile", "nuclear test", "warhead", "nuclear strike", "launch"],
        "nuclear_deescalate": ["de-alert", "arms control", "treaty", "dialogue on strategic stability"]
    },
    "signal_bindings": {
        "mobilization_indicators": {"sources": ["reuters_world", "ap_top", "bbc_world", "aljazeera", "dw_world"], "keywords": ["mobilization"], "window_days": 7},
        "border_clashes": {"sources": ["reuters_world", "ap_top", "bbc_world", "aljazeera"], "keywords": ["border"], "window_days": 7},
        "diplomatic_breakdown": {"sources": ["reuters_world", "bbc_world", "dw_world"], "keywords": ["diplo_break"], "window_days": 10},
        "deescalation_signals": {"sources": ["reuters_world", "bbc_world", "un_news"], "keywords": ["deescalate"], "window_days": 10},
        "domestic_unrest": {"sources": ["reuters_world", "ap_top", "bbc_world", "aljazeera"], "keywords": ["unrest"], "window_days": 7},
        "coup_rumors": {"sources": ["reuters_world", "bbc_world", "dw_world"], "keywords": ["coup"], "window_days": 14},
        "state_repression": {"sources": ["reuters_world", "ap_top", "bbc_world"], "keywords": ["repression"], "window_days": 10},
        "power_sharing": {"sources": ["reuters_world", "bbc_world", "un_news"], "keywords": ["power_sharing"], "window_days": 21},
        "nuclear_testing_talk": {"sources": ["reuters_world", "bbc_world", "dw_world"], "keywords": ["nuclear_weapons"], "window_days": 21},
        "energy_nuclear_incident": {"sources": ["iaea_news"], "keywords": ["nuclear_weapons"], "window_days": 21},
        "dealerting_confidence": {"sources": ["reuters_world", "bbc_world"], "keywords": ["nuclear_deescalate"], "window_days": 30}
    }
}, indent=2)

# Write files
with open(py_path, "w", encoding="utf-8") as f:
    f.write(pam_world_py)

with open(cfg_path, "w", encoding="utf-8") as f:
    f.write(world_cfg)

(py_path.as_posix(), cfg_path.as_posix())
