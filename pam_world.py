#!/usr/bin/env python3
"""
World P.A.M. — Predictive Analytic Machine for Global Scenarios
---------------------------------------------------------------
Evaluates geopolitical, environmental, and social risk hypotheses
based on live public RSS/Atom feeds (Reuters, BBC, UN, etc.).

Usage examples:
  python pam_world.py --list
  python pam_world.py --scenario global_war_risk --simulate 5000 --explain
  python pam_world.py --run-all
  python pam_world.py --help-info
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Tuple, Any, Optional
import json, math, random, argparse, sys, datetime
from urllib import request, error
import xml.etree.ElementTree as ET
from security import (
    fetch_url_secure,
    parse_xml_secure,
    get_allowed_netlocs_from_config,
    MAX_REQUEST_SIZE
)
from validators import validate_config, parse_date, is_within_window
from logger import setup_logging, get_logger
from metrics import get_metrics, Timer
from health import get_health
from cache import get_config_cache, cached
from fetcher import fetch_feeds_parallel, FetchResult
from database import Database
from async_fetcher import AsyncFetcher, fetch_feeds_async
from async_database import AsyncDatabase

# ---------- math helpers ----------
def sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))

def logit(p: float) -> float:
    p = min(max(p, 1e-9), 1 - 1e-9)
    return math.log(p / (1 - p))

# ---------- data classes ----------
@dataclass
class SourceDef:
    name: str
    url: str
    type: str = "rss"
    timeout: float = 10.0

@dataclass
class SignalDef:
    name: str
    weight: float
    description: str = ""
    aggregation: str = "sum"
    cap: float = 1.0

@dataclass
class HypothesisDef:
    name: str
    prior: float
    signals: List[str]

@dataclass
class Config:
    sources: List[SourceDef]
    signals: List[SignalDef]
    hypotheses: List[HypothesisDef]
    keyword_sets: Dict[str, List[str]]
    signal_bindings: Dict[str, Dict[str, Any]]

# ---------- simple fetch + parse ----------
def fetch_url(url: str, timeout: float = 10.0, allowed_netlocs: Optional[set] = None) -> Optional[bytes]:
    """Fetch URL using secure fetching with validation and rate limiting."""
    return fetch_url_secure(url, timeout=timeout, allowed_netlocs=allowed_netlocs)

def _text(node: Optional[ET.Element]) -> str:
    return (node.text or "").strip() if node is not None else ""

def parse_feed_bytes(feed_type: str, data: bytes) -> List[Dict[str, Any]]:
    items = []
    if not data:
        return items
    
    root = parse_xml_secure(data)
    if root is None:
        return items
    
    try:
        tag = "item" if feed_type == "rss" else "{http://www.w3.org/2005/Atom}entry"
        for entry in root.findall(f".//{tag}"):
            title = _text(entry.find("title"))
            summary = _text(entry.find("description")) or _text(entry.find("summary"))
            items.append({"title": title, "summary": summary})
    except ET.ParseError:
        return items
    except Exception:
        return items
    return items

def normalized_keyword_hits(items: List[Dict[str, Any]], keywords: List[str], window_days: int = 7) -> float:
    """
    Count keyword hits within time window and normalize.
    
    Args:
        items: List of feed items with title, summary, and optionally published
        keywords: List of keywords to search for
        window_days: Number of days to look back
        
    Returns:
        Normalized score between 0.0 and 1.0
    """
    if not items or not keywords:
        return 0.0
    
    kw = [k.strip().lower() for k in keywords if k.strip()]
    hits = 0
    
    for it in items:
        text = f"{it.get('title','')} {it.get('summary','')}".lower()
        matched = any(k in text for k in kw)
        if not matched:
            continue
        
        # Check date window
        pub_str = it.get("published") or ""
        pub_date = parse_date(pub_str, window_days)
        if is_within_window(pub_date, window_days):
            hits += 1
    
    # sqrt dampening to avoid one prolific feed dominating
    return min(math.sqrt(hits) / math.sqrt(20.0), 1.0)

# ---------- main engine ----------
class WorldPAM:
    def __init__(self, cfg: Config, db_path: Optional[str] = None, use_async: bool = False):
        self.cfg = cfg
        self.sources = {s.name: s for s in cfg.sources}
        self.signals = {s.name: s for s in cfg.signals}
        self.hyps = {h.name: h for h in cfg.hypotheses}
        # Build allowed netlocs whitelist for security
        self.allowed_netlocs = get_allowed_netlocs_from_config(cfg.sources)
        # Initialize database if path provided
        self.db = Database(db_path) if db_path and not use_async else None
        self.async_db = AsyncDatabase(db_path) if db_path and use_async else None
        self.use_async = use_async

    def compute_signal(self, sig_name: str, country: Optional[str] = None) -> float:
        bind = self.cfg.signal_bindings.get(sig_name, {})
        srcs = bind.get("sources", [])
        kw_sets = bind.get("keywords", [])
        window_days = int(bind.get("window_days", 7))
        
        keywords = []
        for s in kw_sets:
            keywords += self.cfg.keyword_sets.get(s, [])
        if country:
            keywords.append(country)
        
        vals = []
        logger = get_logger("signal")
        
        # Prepare sources for parallel fetching
        source_list = [
            (src_name, self.sources[src_name].url, self.sources[src_name].timeout)
            for src_name in srcs
        ]
        
        # Fetch all feeds in parallel
        fetch_results = fetch_feeds_parallel(
            source_list,
            allowed_netlocs=self.allowed_netlocs,
            max_workers=5
        )
        
        # Process results
        for src_name in srcs:
            result = fetch_results.get(src_name)
            if result and result.success and result.data:
                items = parse_feed_bytes(self.sources[src_name].type, result.data)
                
                # Store feed items in database
                if self.db:
                    for item in items:
                        self.db.store_feed_item(
                            source_name=src_name,
                            url=self.sources[src_name].url,
                            title=item.get("title", ""),
                            summary=item.get("summary", ""),
                            published=item.get("published")
                        )
                    self.db.update_source_status(src_name, success=True)
                
                vals.append(normalized_keyword_hits(items, keywords, window_days=window_days))
            else:
                logger.warning(f"Failed to fetch or parse feed from {src_name}")
                if self.db:
                    error_msg = result.error if result else "Unknown error"
                    self.db.update_source_status(src_name, success=False, error=error_msg)
                vals.append(0.0)  # Default to 0.0 for failed fetches
        
        # Store signal value in database
        if self.db and vals:
            final_val = max(vals) if self.signals[sig_name].aggregation == "max" else sum(vals)
            final_val = min(final_val, self.signals[sig_name].cap)
            self.db.store_signal_value(sig_name, final_val, country=country, window_days=window_days)
        
        if not vals:
            return 0.0
        sig = self.signals[sig_name]
        val = max(vals) if sig.aggregation == "max" else sum(vals)
        return min(val, sig.cap)

    def evaluate(self, hyp_name: str, country: Optional[str] = None, simulate: int = 0):
        hyp = self.hyps[hyp_name]
        z = logit(hyp.prior)
        details = []
        for s in hyp.signals:
            val = self.compute_signal(s, country)
            weight = self.signals[s].weight
            z += weight * val
            details.append((s, val, weight))
        p = sigmoid(z)
        
        mean = None
        ci = None
        
        if simulate:
            sims = []
            for _ in range(simulate):
                z2 = logit(hyp.prior)
                for s, val, w in details:
                    v = 1.0 if random.random() < val else 0.0
                    z2 += w * v
                sims.append(sigmoid(z2))
            sims.sort()
            mean = sum(sims) / len(sims)
            ci = (sims[int(0.05*simulate)], sims[int(0.95*simulate)])
        
        # Store evaluation in database
        if self.db:
            self.db.store_hypothesis_evaluation(
                hypothesis_name=hyp_name,
                probability=p,
                country=country,
                monte_carlo_mean=mean,
                monte_carlo_low=ci[0] if ci else None,
                monte_carlo_high=ci[1] if ci else None
            )
        
        return p, mean, ci, details
    
    async def compute_signal_async(self, sig_name: str, country: Optional[str] = None) -> float:
        """Async version of compute_signal."""
        bind = self.cfg.signal_bindings.get(sig_name, {})
        srcs = bind.get("sources", [])
        kw_sets = bind.get("keywords", [])
        window_days = int(bind.get("window_days", 7))
        
        keywords = []
        for s in kw_sets:
            keywords += self.cfg.keyword_sets.get(s, [])
        if country:
            keywords.append(country)
        
        vals = []
        logger = get_logger("signal")
        
        # Prepare sources for async fetching
        source_list = [
            (src_name, self.sources[src_name].url, self.sources[src_name].timeout)
            for src_name in srcs
        ]
        
        # Fetch all feeds asynchronously
        fetch_results = await fetch_feeds_async(
            source_list,
            allowed_netlocs=self.allowed_netlocs,
            max_concurrent=10
        )
        
        # Process results
        for src_name in srcs:
            result = fetch_results.get(src_name)
            if result and result.success and result.data:
                items = parse_feed_bytes(self.sources[src_name].type, result.data)
                
                # Store feed items in database
                if self.async_db:
                    for item in items:
                        await self.async_db.store_feed_item(
                            source_name=src_name,
                            url=self.sources[src_name].url,
                            title=item.get("title", ""),
                            summary=item.get("summary", ""),
                            published=item.get("published")
                        )
                    await self.async_db.update_source_status(src_name, success=True)
                
                vals.append(normalized_keyword_hits(items, keywords, window_days=window_days))
            else:
                logger.warning(f"Failed to fetch or parse feed from {src_name}")
                if self.async_db:
                    error_msg = result.error if result else "Unknown error"
                    await self.async_db.update_source_status(src_name, success=False, error=error_msg)
                vals.append(0.0)
        
        # Store signal value in database
        if self.async_db and vals:
            final_val = max(vals) if self.signals[sig_name].aggregation == "max" else sum(vals)
            final_val = min(final_val, self.signals[sig_name].cap)
            await self.async_db.store_signal_value(sig_name, final_val, country=country, window_days=window_days)
        
        if not vals:
            return 0.0
        sig = self.signals[sig_name]
        val = max(vals) if sig.aggregation == "max" else sum(vals)
        return min(val, sig.cap)
    
    async def evaluate_async(self, hyp_name: str, country: Optional[str] = None, simulate: int = 0):
        """Async version of evaluate."""
        hyp = self.hyps[hyp_name]
        z = logit(hyp.prior)
        details = []
        for s in hyp.signals:
            val = await self.compute_signal_async(s, country)
            weight = self.signals[s].weight
            z += weight * val
            details.append((s, val, weight))
        p = sigmoid(z)
        
        mean = None
        ci = None
        
        if simulate:
            sims = []
            for _ in range(simulate):
                z2 = logit(hyp.prior)
                for s, val, w in details:
                    v = 1.0 if random.random() < val else 0.0
                    z2 += w * v
                sims.append(sigmoid(z2))
            sims.sort()
            mean = sum(sims) / len(sims)
            ci = (sims[int(0.05*simulate)], sims[int(0.95*simulate)])
        
        # Store evaluation in database
        if self.async_db:
            await self.async_db.store_hypothesis_evaluation(
                hypothesis_name=hyp_name,
                probability=p,
                country=country,
                monte_carlo_mean=mean,
                monte_carlo_low=ci[0] if ci else None,
                monte_carlo_high=ci[1] if ci else None
            )
        
        return p, mean, ci, details

    def interpret(self, name: str, prob: float) -> str:
        if prob < 0.02:
            tone = "very low likelihood"
        elif prob < 0.1:
            tone = "low but notable likelihood"
        elif prob < 0.3:
            tone = "moderate risk that warrants attention"
        elif prob < 0.6:
            tone = "significant and rising probability"
        else:
            tone = "high probability—close watch advised"
        return f"P.A.M. assesses the scenario '{name}' with a {tone} ({prob*100:.1f}%)."

# ---------- util ----------
@cached(ttl_seconds=3600)
def _load_config_impl(path: str, validate: bool = True) -> Config:
    """Internal config loading implementation (cached)."""
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    
    config = Config(
        [SourceDef(**s) for s in raw["sources"]],
        [SignalDef(**s) for s in raw["signals"]],
        [HypothesisDef(**h) for h in raw["hypotheses"]],
        raw["keyword_sets"],
        raw["signal_bindings"]
    )
    
    if validate:
        errors = validate_config(config)
        if errors:
            error_msg = "Configuration validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
            raise ValueError(error_msg)
    
    return config


def load_config(path: str, validate: bool = True) -> Config:
    """
    Load and validate configuration (with caching).
    
    Args:
        path: Path to config JSON file
        validate: Whether to validate the configuration
        
    Returns:
        Config object
        
    Raises:
        FileNotFoundError: If config file doesn't exist
        json.JSONDecodeError: If config is invalid JSON
        ValueError: If validation fails
    """
    # Use cache key based on path and validate flag
    cache = get_config_cache()
    cache_key = f"config:{path}:{validate}"
    
    cached_config = cache.get(cache_key)
    if cached_config is not None:
        return cached_config
    
    config = _load_config_impl(path, validate)
    cache.set(cache_key, config, ttl_seconds=3600)
    return config

# ---------- CLI ----------
def help_info():
    print("""
World P.A.M. — Usage Guide
==========================
Examples:
  python pam_world.py --list
      Show all available hypotheses.

  python pam_world.py --scenario global_war_risk --simulate 5000 --explain
      Evaluate a single scenario with simulation and detailed signal output.

  python pam_world.py --country "Ukraine" --scenario civil_war_risk
      Add a country keyword bias to signal parsing.

  python pam_world.py --run-all
      Run every scenario and print readable summaries.

  python pam_world.py --help-info
      Show this help again.
    """)

def run_all(pam: WorldPAM, simulate: int = 0):
    print("Running all scenarios:\n")
    for name in pam.hyps:
        p, mean, ci, _ = pam.evaluate(name, simulate=simulate)
        line = f"{name:<28} → {p*100:5.1f}%"
        if ci:
            line += f" (avg {mean*100:4.1f}%, range {ci[0]*100:4.1f}–{ci[1]*100:4.1f}%)"
        print(line)
    print("\nTip: use --scenario <name> --explain for detailed breakdowns.\n")

def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--config", default="world_config.json")
    parser.add_argument("--scenario")
    parser.add_argument("--country")
    parser.add_argument("--simulate", type=int, default=0)
    parser.add_argument("--explain", action="store_true")
    parser.add_argument("--run-all", action="store_true")
    parser.add_argument("--help-info", action="store_true")
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    parser.add_argument("--quiet", "-q", action="store_true", help="Suppress non-error output")
    parser.add_argument("--log-file", help="Path to log file")
    parser.add_argument("--health", action="store_true", help="Run health check")
    parser.add_argument("--db-path", default="pam_data.db", help="Path to SQLite database")
    parser.add_argument("--export", help="Export data to JSON file")
    parser.add_argument("--history", help="Show history for scenario (hypothesis name)")
    parser.add_argument("--stats", action="store_true", help="Show statistics")
    parser.add_argument("--cleanup", type=int, metavar="DAYS", help="Clean up data older than N days")
    args = parser.parse_args()
    
    # Setup logging
    log_level = "DEBUG" if args.verbose else ("ERROR" if args.quiet else "INFO")
    setup_logging(
        log_file=args.log_file,
        log_level=log_level,
        console_output=not args.quiet,
        json_format=False
    )
    logger = get_logger()

    if args.health:
        health_status = get_health()
        print(json.dumps(health_status, indent=2))
        return
    
    if args.help_info:
        help_info()
        return

    try:
        logger.info(f"Loading configuration from {args.config}")
        cfg = load_config(args.config, validate=True)
        logger.info(f"Configuration loaded: {len(cfg.sources)} sources, {len(cfg.signals)} signals, {len(cfg.hypotheses)} hypotheses")
    except FileNotFoundError:
        logger.error(f"Config file not found: {args.config}")
        print(f"Error: Config file not found: {args.config}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in config file: {e}")
        print(f"Error: Invalid JSON in config file: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        logger.error(f"Configuration validation failed: {e}")
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    
    pam = WorldPAM(cfg, db_path=args.db_path)
    logger.info("WorldPAM instance created")
    
    # Handle export
    if args.export:
        pam.db.export_to_json(args.export)
        return
    
    # Handle cleanup
    if args.cleanup:
        result = pam.db.cleanup_old_data(days=args.cleanup)
        print(f"Cleaned up: {result}")
        return
    
    # Handle stats
    if args.stats:
        metrics = get_metrics()
        summary = metrics.get_summary()
        print(json.dumps(summary, indent=2))
        return
    
    # Handle history
    if args.history:
        history = pam.db.get_hypothesis_history(args.history, days=30)
        print(f"History for {args.history}:")
        for entry in history[:20]:  # Show last 20
            print(f"  {entry['evaluated_at']}: {entry['probability']*100:.1f}%")
        return

    if args.list:
        try:
            cfg = load_config(args.config, validate=True)
            print("Available scenarios:\n" + "\n".join(f" - {h.name}" for h in cfg.hypotheses))
        except (FileNotFoundError, json.JSONDecodeError, ValueError) as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        return

    if args.run_all:
        run_all(pam, simulate=args.simulate)
        return

    if not args.scenario:
        print("No scenario given. Use --list or --help-info.")
        return

    p, mean, ci, details = pam.evaluate(args.scenario, args.country, simulate=args.simulate)

    print("\n" + pam.interpret(args.scenario, p))
    if mean and ci:
        print(f"Monte Carlo mean: {mean*100:.1f}% (5–95% CI {ci[0]*100:.1f}%–{ci[1]*100:.1f}%)")
    if args.explain:
        print("\nSignal contributions:")
        for name, val, w in details:
            print(f"  {name:24s}  value={val:4.2f}  weight={w:+.2f}  → {val*w:+.3f}")
    print()

if __name__ == "__main__":
    main()
