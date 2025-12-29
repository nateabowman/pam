"""
Parallel feed fetching for World P.A.M.
Uses ThreadPoolExecutor for concurrent HTTP requests.
"""

from typing import List, Dict, Any, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, Future, as_completed
from dataclasses import dataclass
import time
from logger import get_logger
from metrics import get_metrics, Timer
from security import fetch_url_secure
from cache import get_feed_cache


@dataclass
class FetchResult:
    """Result of a feed fetch operation."""
    source_name: str
    url: str
    data: Optional[bytes]
    success: bool
    duration: float
    error: Optional[str] = None


def fetch_single_feed(
    source_name: str,
    url: str,
    timeout: float,
    allowed_netlocs: Optional[set] = None
) -> FetchResult:
    """
    Fetch a single feed.
    
    Args:
        source_name: Name of the source
        url: Feed URL
        timeout: Request timeout
        allowed_netlocs: Allowed network locations
        
    Returns:
        FetchResult with fetch outcome
    """
    start_time = time.time()
    logger = get_logger("fetcher")
    metrics = get_metrics()
    
    try:
        # Check cache first
        cache = get_feed_cache()
        cache_key = f"feed:{url}"
        cached_data = cache.get(cache_key)
        
        if cached_data is not None:
            logger.debug(f"Cache hit for {source_name}")
            metrics.increment("cache_hits", tags={"source": source_name})
            duration = time.time() - start_time
            return FetchResult(
                source_name=source_name,
                url=url,
                data=cached_data,
                success=True,
                duration=duration
            )
        
        # Fetch from network
        with Timer("feed_fetch", tags={"source": source_name}):
            data = fetch_url_secure(url, timeout=timeout, allowed_netlocs=allowed_netlocs)
        
        duration = time.time() - start_time
        
        if data:
            # Cache successful fetch
            cache.set(cache_key, data, ttl_seconds=600)  # 10 minutes
            metrics.increment("http_success", tags={"source": source_name})
            metrics.increment("cache_misses", tags={"source": source_name})
            return FetchResult(
                source_name=source_name,
                url=url,
                data=data,
                success=True,
                duration=duration
            )
        else:
            metrics.increment("http_errors", tags={"source": source_name})
            logger.warning(f"Failed to fetch feed from {source_name}")
            return FetchResult(
                source_name=source_name,
                url=url,
                data=None,
                success=False,
                duration=duration,
                error="Fetch returned None"
            )
    except Exception as e:
        duration = time.time() - start_time
        metrics.increment("http_errors", tags={"source": source_name})
        logger.error(f"Exception fetching {source_name}: {e}")
        return FetchResult(
            source_name=source_name,
            url=url,
            data=None,
            success=False,
            duration=duration,
            error=str(e)
        )


def fetch_feeds_parallel(
    sources: List[Tuple[str, str, float]],  # (name, url, timeout)
    allowed_netlocs: Optional[set] = None,
    max_workers: int = 5
) -> Dict[str, FetchResult]:
    """
    Fetch multiple feeds in parallel.
    
    Args:
        sources: List of (source_name, url, timeout) tuples
        allowed_netlocs: Allowed network locations
        max_workers: Maximum number of concurrent workers
        
    Returns:
        Dictionary mapping source_name to FetchResult
    """
    logger = get_logger("fetcher")
    results: Dict[str, FetchResult] = {}
    
    logger.info(f"Fetching {len(sources)} feeds in parallel (max_workers={max_workers})")
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_source = {
            executor.submit(
                fetch_single_feed,
                source_name,
                url,
                timeout,
                allowed_netlocs
            ): source_name
            for source_name, url, timeout in sources
        }
        
        # Collect results as they complete
        for future in as_completed(future_to_source):
            source_name = future_to_source[future]
            try:
                result = future.result()
                results[source_name] = result
            except Exception as e:
                logger.error(f"Exception in future for {source_name}: {e}")
                results[source_name] = FetchResult(
                    source_name=source_name,
                    url="",
                    data=None,
                    success=False,
                    duration=0.0,
                    error=str(e)
                )
    
    successful = sum(1 for r in results.values() if r.success)
    logger.info(f"Fetched {successful}/{len(sources)} feeds successfully")
    
    return results

