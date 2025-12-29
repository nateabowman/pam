"""
Named Entity Recognition (NER) for extracting geopolitical entities.
Uses rule-based extraction with country/organization lists.
"""

import re
from typing import List, Dict, Any, Set
from logger import get_logger


class EntityExtractor:
    """Rule-based entity extractor for countries, organizations, and people."""
    
    # Common country names
    COUNTRIES = {
        'united states', 'usa', 'us', 'america', 'united kingdom', 'uk', 'britain',
        'russia', 'china', 'france', 'germany', 'japan', 'india', 'brazil',
        'south korea', 'north korea', 'iran', 'iraq', 'syria', 'ukraine',
        'israel', 'palestine', 'saudi arabia', 'egypt', 'turkey', 'pakistan',
        'afghanistan', 'yemen', 'libya', 'sudan', 'ethiopia', 'nigeria',
        'south africa', 'kenya', 'mexico', 'canada', 'australia', 'indonesia',
        'philippines', 'vietnam', 'thailand', 'malaysia', 'singapore', 'taiwan',
        'hong kong', 'bangladesh', 'sri lanka', 'nepal', 'myanmar', 'cambodia',
        'laos', 'mongolia', 'kazakhstan', 'uzbekistan', 'turkmenistan',
        'azerbaijan', 'armenia', 'georgia', 'belarus', 'moldova', 'romania',
        'bulgaria', 'greece', 'serbia', 'croatia', 'bosnia', 'albania',
        'poland', 'czech republic', 'slovakia', 'hungary', 'austria',
        'switzerland', 'sweden', 'norway', 'denmark', 'finland', 'netherlands',
        'belgium', 'spain', 'portugal', 'italy', 'vatican', 'malta', 'cyprus'
    }
    
    # International organizations
    ORGANIZATIONS = {
        'un', 'united nations', 'nato', 'eu', 'european union', 'asean',
        'african union', 'arab league', 'oas', 'organization of american states',
        'g7', 'g20', 'who', 'world health organization', 'iaea', 'international atomic energy agency',
        'imf', 'world bank', 'wto', 'world trade organization', 'red cross',
        'unicef', 'unesco', 'cia', 'fbi', 'nsa', 'pentagon', 'kremlin',
        'white house', 'downing street', 'eurozone', 'eurogroup'
    }
    
    # Common geopolitical terms
    REGIONS = {
        'middle east', 'east asia', 'southeast asia', 'south asia', 'central asia',
        'eastern europe', 'western europe', 'balkans', 'baltic', 'scandinavia',
        'latin america', 'south america', 'north america', 'sub-saharan africa',
        'horn of africa', 'sahel', 'persian gulf', 'south china sea',
        'mediterranean', 'black sea', 'arctic', 'antarctic'
    }
    
    def __init__(self):
        self.logger = get_logger("entity_extractor")
        # Create case-insensitive sets
        self.countries_lower = {c.lower() for c in self.COUNTRIES}
        self.orgs_lower = {o.lower() for o in self.ORGANIZATIONS}
        self.regions_lower = {r.lower() for r in self.REGIONS}
    
    def extract_entities(self, text: str) -> Dict[str, List[str]]:
        """
        Extract entities from text.
        
        Args:
            text: Text to analyze
            
        Returns:
            Dictionary with entity types and lists
        """
        if not text:
            return {
                'countries': [],
                'organizations': [],
                'regions': [],
                'people': []  # Placeholder for future implementation
            }
        
        text_lower = text.lower()
        
        countries = []
        organizations = []
        regions = []
        
        # Extract countries
        for country in self.countries_lower:
            if country in text_lower:
                # Capitalize properly
                country_title = country.title()
                if country_title not in countries:
                    countries.append(country_title)
        
        # Extract organizations
        for org in self.orgs_lower:
            if org in text_lower:
                org_upper = org.upper() if len(org) <= 5 else org.title()
                if org_upper not in organizations:
                    organizations.append(org_upper)
        
        # Extract regions
        for region in self.regions_lower:
            if region in text_lower:
                region_title = region.title()
                if region_title not in regions:
                    regions.append(region_title)
        
        return {
            'countries': countries,
            'organizations': organizations,
            'regions': regions,
            'people': []  # Placeholder
        }
    
    def extract_countries(self, text: str) -> List[str]:
        """Extract country names from text."""
        entities = self.extract_entities(text)
        return entities['countries']
    
    def extract_organizations(self, text: str) -> List[str]:
        """Extract organization names from text."""
        entities = self.extract_entities(text)
        return entities['organizations']
    
    def has_entity(self, text: str, entity: str) -> bool:
        """
        Check if text contains a specific entity.
        
        Args:
            text: Text to check
            entity: Entity name to search for
            
        Returns:
            True if entity found
        """
        text_lower = text.lower()
        entity_lower = entity.lower()
        
        return (
            entity_lower in self.countries_lower and entity_lower in text_lower or
            entity_lower in self.orgs_lower and entity_lower in text_lower or
            entity_lower in self.regions_lower and entity_lower in text_lower
        )

