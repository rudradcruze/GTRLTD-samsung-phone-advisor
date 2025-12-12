"""
RAG Module for Samsung Phone Advisor
Retrieves structured specifications from PostgreSQL and answers factual questions
"""

from sqlalchemy import or_, func
from database import SessionLocal, Phone
import re


class RAGModule:
    """Retrieval-Augmented Generation module for phone specifications"""

    def __init__(self):
        self.db = SessionLocal()

    def __del__(self):
        if hasattr(self, 'db'):
            self.db.close()

    def extract_phone_names(self, query: str) -> list:
        """Extract phone model names from a query"""
        query_lower = query.lower()
        # Normalize query - remove "samsung" as DB stores without it
        query_normalized = query_lower.replace("samsung ", "")

        # Get all phone names from database
        phones = self.db.query(Phone.model_name).all()
        phone_names = [p.model_name for p in phones]

        matched_phones = []

        for phone_name in phone_names:
            name_lower = phone_name.lower()

            # Remove "Galaxy" prefix for core matching
            core_name = name_lower.replace("galaxy ", "").strip()

            # Check exact full name match - must not be followed by a suffix
            name_pattern = r'\b' + re.escape(name_lower) + r'(?!\s*(ultra|plus|\+|fe)\b)(?:\s|$|,|\.|and|or|vs)'
            if re.search(name_pattern, query_normalized):
                matched_phones.append((phone_name, 100))
                continue

            # Check exact core name match - must NOT be followed by a suffix
            # This ensures "s24 ultra" matches only "s24 ultra", not "s24" alone
            core_pattern = r'\b' + re.escape(core_name) + r'(?!\s*(ultra|plus|\+|fe)\b)(?:\s|$|,|\.|and|or|vs)'
            if re.search(core_pattern, query_normalized):
                matched_phones.append((phone_name, 95))
                continue

            # Handle S-series, A-series models with suffixes (Ultra, Plus, FE)
            model_match = re.search(r'^([sazn]\d+)\s*(ultra|plus|\+|fe)?$', core_name, re.IGNORECASE)
            if model_match:
                model_num = model_match.group(1).lower()
                model_suffix = (model_match.group(2) or "").lower().replace("+", "plus")

                # Look for this model number in query with any suffix
                # Use word boundary and capture what comes after
                query_pattern = rf'\b{model_num}\s*(ultra|plus|\+|fe)?\b'
                query_matches = list(re.finditer(query_pattern, query_normalized))

                for qm in query_matches:
                    query_suffix = (qm.group(1) or "").lower().replace("+", "plus")

                    # Both have same suffix (including both empty)
                    if model_suffix == query_suffix:
                        matched_phones.append((phone_name, 90))
                        break
                    # Query has suffix, phone doesn't - skip this phone
                    elif query_suffix and not model_suffix:
                        pass  # Don't add
                    # Query has no suffix, phone has suffix - only add if no exact match exists
                    elif not query_suffix and model_suffix:
                        matched_phones.append((phone_name, 30))
                        break
                continue

            # Handle Z Fold/Flip series
            fold_match = re.search(r'^z\s*(fold|flip)\s*(\d+)?\s*(fe|special)?$', core_name, re.IGNORECASE)
            if fold_match:
                series_type = fold_match.group(1).lower()
                version = fold_match.group(2) or ""
                variant = (fold_match.group(3) or "").lower()

                query_fold_pattern = rf'\bz\s*{series_type}\s*(\d+)?\s*(fe|special)?\b'
                query_fold_match = re.search(query_fold_pattern, query_normalized)

                if query_fold_match:
                    query_version = query_fold_match.group(1) or ""
                    query_variant = (query_fold_match.group(2) or "").lower()

                    if version == query_version and variant == query_variant:
                        matched_phones.append((phone_name, 90))
                    elif version == query_version and not query_variant and not variant:
                        matched_phones.append((phone_name, 90))
                    elif version == query_version and not query_variant:
                        matched_phones.append((phone_name, 40))

        # Sort by score descending
        matched_phones.sort(key=lambda x: x[1], reverse=True)

        # Return unique phones with high scores only
        # For comparisons, we want exact matches
        result = []
        seen = set()
        for phone, score in matched_phones:
            if score >= 80 and phone not in seen:  # Only high confidence matches
                result.append(phone)
                seen.add(phone)

        # If no high-confidence matches, include lower ones
        if not result:
            for phone, score in matched_phones:
                if score >= 30 and phone not in seen:
                    result.append(phone)
                    seen.add(phone)

        return result

    def get_phone_by_name(self, name: str) -> Phone:
        """Get a phone by its model name (fuzzy match)"""
        name_lower = name.lower()

        # First try exact match
        phone = self.db.query(Phone).filter(
            func.lower(Phone.model_name) == name_lower
        ).first()

        if phone:
            return phone

        # Try contains match
        phone = self.db.query(Phone).filter(
            func.lower(Phone.model_name).contains(name_lower)
        ).first()

        if phone:
            return phone

        # Try matching without "Samsung Galaxy" prefix
        search_terms = name_lower.replace("samsung", "").replace("galaxy", "").strip()
        if search_terms:
            phone = self.db.query(Phone).filter(
                func.lower(Phone.model_name).contains(search_terms)
            ).first()

        return phone

    def get_all_phones(self) -> list:
        """Get all phones from database"""
        return self.db.query(Phone).all()

    def search_phones_by_criteria(self, criteria: dict) -> list:
        """Search phones by various criteria"""
        query = self.db.query(Phone)

        if 'price_max' in criteria:
            # Extract numeric price and filter
            phones = query.all()
            filtered = []
            for phone in phones:
                price = self._extract_price(phone.price)
                if price and price <= criteria['price_max']:
                    filtered.append(phone)
            return filtered

        if 'battery_min' in criteria:
            phones = query.all()
            filtered = []
            for phone in phones:
                battery = self._extract_battery(phone.battery)
                if battery and battery >= criteria['battery_min']:
                    filtered.append(phone)
            return filtered

        if 'ram_min' in criteria:
            phones = query.all()
            filtered = []
            for phone in phones:
                ram = self._extract_ram(phone.ram)
                if ram and ram >= criteria['ram_min']:
                    filtered.append(phone)
            return filtered

        return query.all()

    def _extract_price(self, price_str: str) -> float:
        """Extract numeric price from price string"""
        if not price_str or price_str == 'N/A':
            return None

        # Try to find USD price first (handles formats like "$1299", "$ 1,049.99", "$499.94")
        match = re.search(r'\$\s*([\d,]+\.?\d*)', price_str)
        if match:
            return float(match.group(1).replace(',', ''))

        # Try EUR price
        match = re.search(r'€\s*([\d,]+\.?\d*)', price_str)
        if match:
            return float(match.group(1).replace(',', ''))

        return None

    def _extract_battery(self, battery_str: str) -> int:
        """Extract battery capacity in mAh"""
        if not battery_str or battery_str == 'N/A':
            return None

        match = re.search(r'(\d+)\s*mAh', battery_str, re.IGNORECASE)
        if match:
            return int(match.group(1))

        return None

    def _extract_ram(self, ram_str: str) -> int:
        """Extract RAM in GB"""
        if not ram_str or ram_str == 'N/A':
            return None

        match = re.search(r'(\d+)\s*GB', ram_str, re.IGNORECASE)
        if match:
            return int(match.group(1))

        return None

    def retrieve_specs(self, query: str) -> dict:
        """
        Main retrieval function for RAG
        Returns relevant phone specifications based on the query
        """
        result = {
            'phones': [],
            'query_type': 'unknown',
            'criteria': {}
        }

        query_lower = query.lower()

        # Determine query type
        if any(word in query_lower for word in ['compare', 'versus', 'vs', 'difference', 'better']):
            result['query_type'] = 'comparison'
        elif any(word in query_lower for word in ['best', 'recommend', 'which', 'should i', 'top']):
            result['query_type'] = 'recommendation'
        elif any(word in query_lower for word in ['spec', 'feature', 'detail', 'what is', 'what are', 'tell me about']):
            result['query_type'] = 'specs'
        else:
            result['query_type'] = 'general'

        # Extract price constraint
        price_match = re.search(r'under\s*\$?(\d+)', query_lower)
        if price_match:
            result['criteria']['price_max'] = float(price_match.group(1))

        price_match = re.search(r'below\s*\$?(\d+)', query_lower)
        if price_match:
            result['criteria']['price_max'] = float(price_match.group(1))

        # Extract battery preference
        if 'battery' in query_lower or 'long lasting' in query_lower:
            result['criteria']['focus'] = 'battery'

        # Extract camera preference
        if 'camera' in query_lower or 'photo' in query_lower or 'photography' in query_lower:
            result['criteria']['focus'] = 'camera'

        # Extract display preference
        if 'display' in query_lower or 'screen' in query_lower:
            result['criteria']['focus'] = 'display'

        # Find mentioned phones
        mentioned_phones = self.extract_phone_names(query)

        if mentioned_phones:
            for phone_name in mentioned_phones:
                phone = self.get_phone_by_name(phone_name)
                if phone:
                    result['phones'].append(phone.to_dict())
        elif 'price_max' in result['criteria']:
            # Get phones under price
            phones = self.search_phones_by_criteria({'price_max': result['criteria']['price_max']})
            result['phones'] = [p.to_dict() for p in phones[:10]]
        elif result['query_type'] == 'recommendation':
            # Get all phones for recommendation
            phones = self.get_all_phones()
            result['phones'] = [p.to_dict() for p in phones]

        return result

    def format_specs_for_display(self, phone: dict) -> str:
        """Format phone specifications for display"""
        return f"""
**{phone['model_name']}**
- Release: {phone['release_date']}
- Display: {phone['display']}
- Battery: {phone['battery']}
- Camera: {phone['camera']}
- RAM: {phone['ram']}
- Storage: {phone['storage']}
- Chipset: {phone['chipset']}
- OS: {phone['os']}
- Price: {phone['price']}
"""


# Singleton instance
_rag_instance = None


def get_rag_module() -> RAGModule:
    global _rag_instance
    if _rag_instance is None:
        _rag_instance = RAGModule()
    return _rag_instance
