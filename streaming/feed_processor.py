"""
Real-time feed processor with change detection.
"""

import hashlib
from typing import Dict, List, Optional
from datetime import datetime
from logger import get_logger
from async_fetcher import AsyncFetcher
from streaming.event_bus import get_event_bus, Event


class FeedProcessor:
    """Processes feeds in real-time and detects changes."""
    
    def __init__(self):
        self.logger = get_logger("feed_processor")
        self.event_bus = get_event_bus()
        self.last_hashes: Dict[str, str] = {}
    
    def _calculate_feed_hash(self, items: List[Dict]) -> str:
        """Calculate hash of feed items."""
        content = "".join(
            f"{item.get('title', '')}{item.get('summary', '')}"
            for item in items[:10]  # Use first 10 items
        )
        return hashlib.md5(content.encode()).hexdigest()
    
    async def process_feed(
        self,
        source_name: str,
        url: str,
        feed_type: str = "rss"
    ) -> bool:
        """
        Process a feed and detect changes.
        
        Args:
            source_name: Name of the source
            url: Feed URL
            feed_type: Type of feed (rss/atom)
            
        Returns:
            True if feed was updated
        """
        try:
            # Fetch feed
            async with AsyncFetcher() as fetcher:
                result = await fetcher.fetch_single_feed(source_name, url)
            
            if not result.success or not result.data:
                return False
            
            # Parse feed
            from pam_world import parse_feed_bytes
            items = parse_feed_bytes(feed_type, result.data)
            
            if not items:
                return False
            
            # Check for changes
            current_hash = self._calculate_feed_hash(items)
            last_hash = self.last_hashes.get(source_name)
            
            if current_hash != last_hash:
                # Feed updated
                self.last_hashes[source_name] = current_hash
                
                # Publish event
                await self.event_bus.publish(Event(
                    event_type="feed_updated",
                    payload={
                        "source": source_name,
                        "url": url,
                        "item_count": len(items),
                        "items": items[:5]  # First 5 items
                    },
                    timestamp=datetime.utcnow().isoformat() + "Z",
                    source=source_name
                ))
                
                self.logger.info(f"Feed updated: {source_name} ({len(items)} items)")
                return True
            
            return False
        
        except Exception as e:
            self.logger.error(f"Error processing feed {source_name}: {e}")
            return False
    
    async def process_feeds_continuously(
        self,
        sources: List[Dict[str, str]],
        interval_seconds: int = 300
    ):
        """
        Continuously process feeds at intervals.
        
        Args:
            sources: List of source dictionaries with name, url, type
            interval_seconds: Interval between checks
        """
        import asyncio
        
        self.logger.info(f"Starting continuous feed processing for {len(sources)} sources")
        
        while True:
            try:
                for source in sources:
                    await self.process_feed(
                        source["name"],
                        source["url"],
                        source.get("type", "rss")
                    )
                    await asyncio.sleep(1)  # Small delay between feeds
                
                await asyncio.sleep(interval_seconds)
            except asyncio.CancelledError:
                self.logger.info("Feed processing cancelled")
                break
            except Exception as e:
                self.logger.error(f"Error in continuous processing: {e}")
                await asyncio.sleep(interval_seconds)

