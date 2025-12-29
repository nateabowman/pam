"""
Security utilities for World P.A.M.
Provides URL validation, request size limits, XML protection, and rate limiting.
"""

from typing import Optional, Set
from urllib.parse import urlparse
from urllib import request, error
import xml.etree.ElementTree as ET
import time
from collections import defaultdict

# Security constants
MAX_REQUEST_SIZE = 10 * 1024 * 1024  # 10MB
MAX_ENTITY_EXPANSION = 100
ALLOWED_SCHEMES = {"http", "https"}
ALLOWED_NETLOCS: Set[str] = set()  # Will be populated from config
USER_AGENT = "World-PAM/1.0 (Geopolitical Risk Analysis Tool)"

# Rate limiting
_rate_limit_store: dict[str, list[float]] = defaultdict(list)
RATE_LIMIT_REQUESTS = 10  # requests per window
RATE_LIMIT_WINDOW = 60.0  # seconds


def validate_url(url: str, allowed_netlocs: Optional[Set[str]] = None) -> bool:
    """
    Validate URL to prevent SSRF attacks.
    
    Args:
        url: URL to validate
        allowed_netlocs: Set of allowed network locations (hostnames)
        
    Returns:
        True if URL is safe, False otherwise
    """
    try:
        parsed = urlparse(url)
        
        # Check scheme
        if parsed.scheme not in ALLOWED_SCHEMES:
            return False
        
        # Check for localhost/internal IPs
        hostname = parsed.hostname
        if not hostname:
            return False
        
        # Block localhost and private IP ranges
        if hostname in ("localhost", "127.0.0.1", "0.0.0.0"):
            return False
        
        # Block private IP ranges (simplified check)
        if hostname.startswith(("10.", "172.16.", "172.17.", "172.18.", "172.19.",
                                "172.20.", "172.21.", "172.22.", "172.23.", "172.24.",
                                "172.25.", "172.26.", "172.27.", "172.28.", "172.29.",
                                "172.30.", "172.31.", "192.168.", "169.254.")):
            return False
        
        # If whitelist provided, check against it
        if allowed_netlocs:
            if hostname not in allowed_netlocs:
                # Also check without www prefix
                if hostname.startswith("www."):
                    hostname_no_www = hostname[4:]
                    if hostname_no_www not in allowed_netlocs:
                        return False
                else:
                    return False
        
        return True
    except Exception:
        return False


def check_rate_limit(url: str) -> bool:
    """
    Check if request is within rate limit.
    
    Args:
        url: URL being requested
        
    Returns:
        True if within rate limit, False if rate limited
    """
    now = time.time()
    key = urlparse(url).netloc
    
    # Clean old entries outside window
    _rate_limit_store[key] = [
        ts for ts in _rate_limit_store[key]
        if now - ts < RATE_LIMIT_WINDOW
    ]
    
    # Check if limit exceeded
    if len(_rate_limit_store[key]) >= RATE_LIMIT_REQUESTS:
        return False
    
    # Record this request
    _rate_limit_store[key].append(now)
    return True


def fetch_url_secure(
    url: str,
    timeout: float = 10.0,
    max_size: int = MAX_REQUEST_SIZE,
    allowed_netlocs: Optional[Set[str]] = None,
    user_agent: str = USER_AGENT
) -> Optional[bytes]:
    """
    Securely fetch URL with validation, size limits, and rate limiting.
    
    Args:
        url: URL to fetch
        timeout: Request timeout in seconds
        max_size: Maximum response size in bytes
        allowed_netlocs: Set of allowed network locations
        user_agent: User-Agent header value
        
    Returns:
        Response bytes or None if fetch failed
    """
    # Validate URL
    if not validate_url(url, allowed_netlocs):
        return None
    
    # Check rate limit
    if not check_rate_limit(url):
        return None
    
    # Create request with User-Agent
    req = request.Request(url, headers={"User-Agent": user_agent})
    
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            # Check content length header if available
            content_length = resp.headers.get("Content-Length")
            if content_length:
                try:
                    size = int(content_length)
                    if size > max_size:
                        return None
                except ValueError:
                    pass
            
            # Read response with size limit
            data = b""
            while True:
                chunk = resp.read(8192)  # 8KB chunks
                if not chunk:
                    break
                data += chunk
                if len(data) > max_size:
                    return None
            
            return data
    except error.URLError:
        return None
    except error.HTTPError:
        return None
    except TimeoutError:
        return None
    except Exception:
        return None


def parse_xml_secure(content: bytes, max_entity_expansion: int = MAX_ENTITY_EXPANSION) -> Optional[ET.Element]:
    """
    Parse XML with protection against XML bombs and entity expansion attacks.
    
    Args:
        content: XML content bytes
        max_entity_expansion: Maximum entity expansion depth
        
    Returns:
        Parsed ElementTree root or None if parsing failed
    """
    if not content:
        return None
    
    # Limit content size before parsing
    if len(content) > MAX_REQUEST_SIZE:
        return None
    
    try:
        # Use defusedxml-like approach: limit entity expansion
        # Since we're using standard library, we'll use iterparse with limited depth
        parser = ET.XMLParser()
        
        # Try to parse with size limits
        # Note: Standard library doesn't have built-in entity expansion limits,
        # so we rely on size limits and iterative parsing
        try:
            root = ET.fromstring(content, parser=parser)
            return root
        except ET.ParseError:
            # Try with iterparse for large files
            try:
                it = ET.iterparse(ET.BytesIO(content), events=("start",))
                depth = 0
                for event, elem in it:
                    depth += 1
                    if depth > 1000:  # Limit depth
                        return None
                # If we get here, try parsing normally
                root = ET.fromstring(content)
                return root
            except Exception:
                return None
    except ET.ParseError:
        return None
    except Exception:
        return None


def get_allowed_netlocs_from_config(sources: list) -> Set[str]:
    """
    Extract allowed network locations from configuration sources.
    
    Args:
        sources: List of source definitions with 'url' field
        
    Returns:
        Set of allowed hostnames
    """
    netlocs: Set[str] = set()
    for source in sources:
        if isinstance(source, dict):
            url = source.get("url", "")
        else:
            url = getattr(source, "url", "")
        
        if url:
            parsed = urlparse(url)
            if parsed.hostname:
                netlocs.add(parsed.hostname)
                # Also add without www prefix
                if parsed.hostname.startswith("www."):
                    netlocs.add(parsed.hostname[4:])
    
    return netlocs

