"""
Async feed fetching for World P.A.M.
Uses asyncio and aiohttp for concurrent HTTP requests.
"""

import asyncio
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import time
import aiohttp
from logger import get_logger
from metrics import get_metrics, Timer
from security import validate_url, check_rate_limit, get_allowed_netlocs_from_config, MAX_REQUEST_SIZE, USER_AGENT
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


class AsyncFetcher:
    """Async HTTP client with connection pooling."""
    
    def __init__(self, allowed_netlocs: Optional[set] = None):
        """
        Initialize async fetcher.
        
        Args:
            allowed_netlocs: Set of allowed network locations
        """
        self.allowed_netlocs = allowed_netlocs
        self.session: Optional[aiohttp.ClientSession] = None
        self.logger = get_logger("async_fetcher")
        self.metrics = get_metrics()
    
    async def __aenter__(self):
        """Async context manager entry."""
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        connector = aiohttp.TCPConnector(limit=100, limit_per_host=10)
        self.session = aiohttp.ClientSession(
            timeout=timeout,
            connector=connector,
            headers={"User-Agent": USER_AGENT}
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def fetch_single_feed(
        self,
        source_name: str,
        url: str,
        timeout: float = 10.0
    ) -> FetchResult:
        """
        Fetch a single feed asynchronously.
        
        Args:
            source_name: Name of the source
            url: Feed URL
            timeout: Request timeout
            
        Returns:
            FetchResult with fetch outcome
        """
        start_time = time.time()
        
        try:
            # Validate URL
            if not validate_url(url, self.allowed_netlocs):
                return FetchResult(
                    source_name=source_name,
                    url=url,
                    data=None,
                    success=False,
                    duration=time.time() - start_time,
                    error="URL validation failed"
                )
            
            # Check rate limit
            if not check_rate_limit(url):
                return FetchResult(
                    source_name=source_name,
                    url=url,
                    data=None,
                    success=False,
                    duration=time.time() - start_time,
                    error="Rate limit exceeded"
                )
            
            # Check cache first
            cache = get_feed_cache()
            cache_key = f"feed:{url}"
            cached_data = cache.get(cache_key)
            
            if cached_data is not None:
                self.logger.debug(f"Cache hit for {source_name}")
                self.metrics.increment("cache_hits", tags={"source": source_name})
                duration = time.time() - start_time
                return FetchResult(
                    source_name=source_name,
                    url=url,
                    data=cached_data,
                    success=True,
                    duration=duration
                )
            
            # Fetch from network
            if not self.session:
                raise RuntimeError("Session not initialized. Use async context manager.")
            
            async with Timer("feed_fetch", tags={"source": source_name}):
                async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
                    if resp.status != 200:
                        raise aiohttp.ClientResponseError(
                            request_info=resp.request_info,
                            history=resp.history,
                            status=resp.status
                        )
                    
                    # Read with size limit
                    data = b""
                    async for chunk in resp.content.iter_chunked(8192):
                        data += chunk
                        if len(data) > MAX_REQUEST_SIZE:
                            return FetchResult(
                                source_name=source_name,
                                url=url,
                                data=None,
                                success=False,
                                duration=time.time() - start_time,
                                error="Response too large"
                            )
            
            duration = time.time() - start_time
            
            if data:
                # Cache successful fetch
                cache.set(cache_key, data, ttl_seconds=600)  # 10 minutes
                self.metrics.increment("http_success", tags={"source": source_name})
                self.metrics.increment("cache_misses", tags={"source": source_name})
                return FetchResult(
                    source_name=source_name,
                    url=url,
                    data=data,
                    success=True,
                    duration=duration
                )
            else:
                self.metrics.increment("http_errors", tags={"source": source_name})
                self.logger.warning(f"Failed to fetch feed from {source_name}")
                return FetchResult(
                    source_name=source_name,
                    url=url,
                    data=None,
                    success=False,
                    duration=duration,
                    error="Empty response"
                )
        except asyncio.TimeoutError:
            duration = time.time() - start_time
            self.metrics.increment("http_errors", tags={"source": source_name})
            self.logger.error(f"Timeout fetching {source_name}")
            return FetchResult(
                source_name=source_name,
                url=url,
                data=None,
                success=False,
                duration=duration,
                error="Timeout"
            )
        except Exception as e:
            duration = time.time() - start_time
            self.metrics.increment("http_errors", tags={"source": source_name})
            self.logger.error(f"Exception fetching {source_name}: {e}")
            return FetchResult(
                source_name=source_name,
                url=url,
                data=None,
                success=False,
                duration=duration,
                error=str(e)
            )
    
    async def fetch_feeds_parallel(
        self,
        sources: List[Tuple[str, str, float]],  # (name, url, timeout)
        max_concurrent: int = 10
    ) -> Dict[str, FetchResult]:
        """
        Fetch multiple feeds in parallel.
        
        Args:
            sources: List of (source_name, url, timeout) tuples
            max_concurrent: Maximum number of concurrent requests
            
        Returns:
            Dictionary mapping source_name to FetchResult
        """
        self.logger.info(f"Fetching {len(sources)} feeds asynchronously (max_concurrent={max_concurrent})")
        
        # Create semaphore to limit concurrent requests
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def fetch_with_semaphore(source_name: str, url: str, timeout: float):
            async with semaphore:
                return await self.fetch_single_feed(source_name, url, timeout)
        
        # Create all tasks
        tasks = [
            fetch_with_semaphore(source_name, url, timeout)
            for source_name, url, timeout in sources
        ]
        
        # Execute all tasks concurrently
        results_list = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        results: Dict[str, FetchResult] = {}
        for i, result in enumerate(results_list):
            source_name = sources[i][0]
            if isinstance(result, Exception):
                self.logger.error(f"Exception in task for {source_name}: {result}")
                results[source_name] = FetchResult(
                    source_name=source_name,
                    url="",
                    data=None,
                    success=False,
                    duration=0.0,
                    error=str(result)
                )
            else:
                results[source_name] = result
        
        successful = sum(1 for r in results.values() if r.success)
        self.logger.info(f"Fetched {successful}/{len(sources)} feeds successfully")
        
        return results


async def fetch_feeds_async(
    sources: List[Tuple[str, str, float]],
    allowed_netlocs: Optional[set] = None,
    max_concurrent: int = 10
) -> Dict[str, FetchResult]:
    """
    Convenience function for async feed fetching.
    
    Args:
        sources: List of (source_name, url, timeout) tuples
        allowed_netlocs: Allowed network locations
        max_concurrent: Maximum concurrent requests
        
    Returns:
        Dictionary mapping source_name to FetchResult
    """
    async with AsyncFetcher(allowed_netlocs=allowed_netlocs) as fetcher:
        return await fetcher.fetch_feeds_parallel(sources, max_concurrent=max_concurrent)

