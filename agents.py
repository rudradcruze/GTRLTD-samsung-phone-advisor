"""
Multi-Agent System for Samsung Phone Advisor
Agent 1 - Data Extractor: Pulls relevant phone data from PostgreSQL
Agent 2 - Review Generator: Generates comparative analysis or recommendations
"""

import os
import google.generativeai as genai
from config import GEMINI_API_KEY
from rag_module import get_rag_module
import re


class DataExtractorAgent:
    """
    Agent 1: Data Extractor
    Responsible for pulling relevant phone data from PostgreSQL based on the query
    """

    def __init__(self):
        self.rag = get_rag_module()

    def extract_data(self, query: str) -> dict:
        """
        Extract relevant phone data based on the user query
        Returns structured data for the Review Generator
        """
        # Use RAG module to retrieve relevant data
        retrieval_result = self.rag.retrieve_specs(query)

        extracted_data = {
            'query': query,
            'query_type': retrieval_result['query_type'],
            'criteria': retrieval_result['criteria'],
            'phones': retrieval_result['phones'],
            'phone_count': len(retrieval_result['phones'])
        }

        # Add specific data based on query type
        if retrieval_result['query_type'] == 'comparison' and len(retrieval_result['phones']) >= 2:
            extracted_data['comparison_data'] = self._prepare_comparison(retrieval_result['phones'])
        elif retrieval_result['query_type'] == 'recommendation':
            extracted_data['recommendation_data'] = self._prepare_recommendations(
                retrieval_result['phones'],
                retrieval_result['criteria']
            )

        return extracted_data

    def _prepare_comparison(self, phones: list) -> dict:
        """Prepare side-by-side comparison data"""
        if len(phones) < 2:
            return {}

        phone1, phone2 = phones[0], phones[1]

        comparison = {
            'phone1': phone1,
            'phone2': phone2,
            'differences': []
        }

        # Compare key specs
        specs_to_compare = ['display', 'battery', 'camera', 'ram', 'storage', 'chipset', 'price']

        for spec in specs_to_compare:
            if phone1.get(spec) != phone2.get(spec):
                comparison['differences'].append({
                    'spec': spec,
                    'phone1_value': phone1.get(spec, 'N/A'),
                    'phone2_value': phone2.get(spec, 'N/A')
                })

        return comparison

    def _prepare_recommendations(self, phones: list, criteria: dict) -> dict:
        """Prepare recommendation data based on criteria"""
        recommendations = {
            'criteria': criteria,
            'candidates': phones,
            'top_picks': []
        }

        focus = criteria.get('focus', 'overall')

        # Score and rank phones based on criteria
        scored_phones = []
        for phone in phones:
            score = self._score_phone(phone, focus, criteria)
            scored_phones.append((phone, score))

        # Sort by score descending
        scored_phones.sort(key=lambda x: x[1], reverse=True)

        # Top 3 recommendations
        recommendations['top_picks'] = [p[0] for p in scored_phones[:3]]

        return recommendations

    def _score_phone(self, phone: dict, focus: str, criteria: dict) -> float:
        """Score a phone based on focus area and criteria"""
        score = 0

        # Base score from battery
        battery_match = re.search(r'(\d+)\s*mAh', phone.get('battery', ''), re.IGNORECASE)
        if battery_match:
            battery_mah = int(battery_match.group(1))
            score += battery_mah / 1000  # Normalize

        # Camera score (based on MP)
        camera_match = re.search(r'(\d+)\s*MP', phone.get('camera', ''), re.IGNORECASE)
        if camera_match:
            main_mp = int(camera_match.group(1))
            score += main_mp / 50  # Normalize

        # RAM score
        ram_match = re.search(r'(\d+)\s*GB', phone.get('ram', ''), re.IGNORECASE)
        if ram_match:
            ram_gb = int(ram_match.group(1))
            score += ram_gb / 4  # Normalize

        # Focus area bonus
        if focus == 'battery':
            if battery_match:
                score += battery_mah / 500
        elif focus == 'camera':
            if camera_match:
                score += main_mp / 25
        elif focus == 'display':
            if '120hz' in phone.get('display', '').lower():
                score += 2
            if 'amoled' in phone.get('display', '').lower():
                score += 1

        # Price penalty if over budget
        if 'price_max' in criteria:
            price_match = re.search(r'\$(\d+)', phone.get('price', ''))
            if price_match:
                price = float(price_match.group(1))
                if price <= criteria['price_max']:
                    score += 3  # Bonus for being under budget
                else:
                    score -= 5  # Penalty for over budget

        return score


class ReviewGeneratorAgent:
    """
    Agent 2: Review Generator
    Responsible for generating comparative analysis or recommendations in natural language
    """

    def __init__(self):
        self.model = None
        self.fallback_model = None
        if GEMINI_API_KEY and GEMINI_API_KEY != "your_gemini_api_key_here":
            genai.configure(api_key=GEMINI_API_KEY)
            # Try gemini-2.0-flash first (may require paid tier)
            self.model = genai.GenerativeModel('gemini-2.0-flash')
            # Fallback to gemini-pro (available on free tier)
            self.fallback_model = genai.GenerativeModel('gemini-pro')

    def generate_review(self, extracted_data: dict) -> str:
        """
        Generate a natural language review/recommendation based on extracted data
        """
        query_type = extracted_data.get('query_type', 'general')
        phones = extracted_data.get('phones', [])

        if not phones:
            return "I couldn't find any Samsung phones matching your query. Please try rephrasing your question or ask about specific models like Galaxy S24 Ultra, S23, A54, etc."

        # Try using Gemini if available
        if self.model:
            return self._generate_with_llm(extracted_data)

        # Fallback to template-based generation
        if query_type == 'comparison':
            return self._generate_comparison_review(extracted_data)
        elif query_type == 'recommendation':
            return self._generate_recommendation_review(extracted_data)
        elif query_type == 'specs':
            return self._generate_specs_review(extracted_data)
        else:
            return self._generate_general_review(extracted_data)

    def _generate_with_llm(self, extracted_data: dict) -> str:
        """Generate review using Google Gemini LLM"""
        if not self.model and not self.fallback_model:
            # Fallback if no models were initialized
            query_type = extracted_data.get('query_type', 'general')
            if query_type == 'comparison':
                return self._generate_comparison_review(extracted_data)
            elif query_type == 'recommendation':
                return self._generate_recommendation_review(extracted_data)
            else:
                return self._generate_specs_review(extracted_data)
        
        # Prepare context for LLM
        phones_context = ""
        for phone in extracted_data.get('phones', [])[:5]:
            phones_context += f"""
Phone: {phone.get('model_name')}
- Release: {phone.get('release_date')}
- Display: {phone.get('display')}
- Battery: {phone.get('battery')}
- Camera: {phone.get('camera')}
- RAM: {phone.get('ram')}
- Storage: {phone.get('storage')}
- Chipset: {phone.get('chipset')}
- Price: {phone.get('price')}
"""

        query = extracted_data.get('query', '')
        query_type = extracted_data.get('query_type', 'general')
        criteria = extracted_data.get('criteria', {})

        prompt = f"""You are a Samsung phone expert assistant. Based on the following phone data, answer the user's question.

User Question: {query}
Query Type: {query_type}
Criteria: {criteria}

Available Phone Data:
{phones_context}

Provide a helpful, concise response that:
1. Directly answers the user's question
2. Includes relevant specifications
3. Gives clear recommendations if asked
4. Highlights key differences in comparisons
Keep the response under 200 words and focus on the most relevant information."""

        # Try primary model first (gemini-2.0-flash)
        if self.model:
            try:
                response = self.model.generate_content(prompt)
                return response.text
            except Exception as e:
                error_str = str(e)
                # Check if it's a quota/rate limit error
                if '429' in error_str or 'quota' in error_str.lower() or 'rate' in error_str.lower():
                    print(f"Quota/rate limit exceeded for gemini-2.0-flash, falling back to gemini-pro: {e}")
                    # Try fallback model
                    if self.fallback_model:
                        try:
                            response = self.fallback_model.generate_content(prompt)
                            return response.text
                        except Exception as fallback_error:
                            print(f"Fallback model also failed: {fallback_error}")
                else:
                    print(f"LLM generation failed: {e}")

        # Try fallback model if primary model doesn't exist
        if self.fallback_model:
            try:
                response = self.fallback_model.generate_content(prompt)
                return response.text
            except Exception as e:
                print(f"Fallback model generation failed: {e}")

        # Final fallback to template-based
        query_type = extracted_data.get('query_type', 'general')
        if query_type == 'comparison':
            return self._generate_comparison_review(extracted_data)
        elif query_type == 'recommendation':
            return self._generate_recommendation_review(extracted_data)
        else:
            return self._generate_specs_review(extracted_data)

    def _generate_specs_review(self, extracted_data: dict) -> str:
        """Generate specs-focused response"""
        phones = extracted_data.get('phones', [])
        if not phones:
            return "No phones found matching your query."

        phone = phones[0]
        response = f"{phone.get('model_name')} specifications:\n\n"
        response += f"• Display: {phone.get('display')}\n"
        response += f"• Battery: {phone.get('battery')}\n"
        response += f"• Camera: {phone.get('camera')}\n"
        response += f"• RAM: {phone.get('ram')}\n"
        response += f"• Storage: {phone.get('storage')}\n"
        response += f"• Chipset: {phone.get('chipset')}\n"
        response += f"• OS: {phone.get('os')}\n"
        response += f"• Price: {phone.get('price')}\n"
        response += f"• Released: {phone.get('release_date')}"

        return response

    def _generate_comparison_review(self, extracted_data: dict) -> str:
        """Generate comparison-focused response"""
        comparison_data = extracted_data.get('comparison_data', {})
        phones = extracted_data.get('phones', [])

        if not comparison_data or len(phones) < 2:
            if len(phones) == 1:
                return self._generate_specs_review(extracted_data)
            return "Please specify two phones to compare."

        phone1 = comparison_data['phone1']
        phone2 = comparison_data['phone2']
        criteria = extracted_data.get('criteria', {})
        focus = criteria.get('focus', 'overall')

        response = f"Comparing {phone1.get('model_name')} vs {phone2.get('model_name')}:\n\n"

        # Display comparison
        response += f"📱 Display:\n"
        response += f"  • {phone1.get('model_name')}: {phone1.get('display')}\n"
        response += f"  • {phone2.get('model_name')}: {phone2.get('display')}\n\n"

        # Battery comparison
        response += f"🔋 Battery:\n"
        response += f"  • {phone1.get('model_name')}: {phone1.get('battery')}\n"
        response += f"  • {phone2.get('model_name')}: {phone2.get('battery')}\n\n"

        # Camera comparison
        response += f"📷 Camera:\n"
        response += f"  • {phone1.get('model_name')}: {phone1.get('camera')}\n"
        response += f"  • {phone2.get('model_name')}: {phone2.get('camera')}\n\n"

        # Price comparison
        response += f"💰 Price:\n"
        response += f"  • {phone1.get('model_name')}: {phone1.get('price')}\n"
        response += f"  • {phone2.get('model_name')}: {phone2.get('price')}\n\n"

        # Recommendation based on focus
        response += "📝 Recommendation:\n"

        if focus == 'camera' or 'photo' in extracted_data.get('query', '').lower():
            # Compare camera MPs
            cam1_match = re.search(r'(\d+)\s*MP', phone1.get('camera', ''))
            cam2_match = re.search(r'(\d+)\s*MP', phone2.get('camera', ''))

            if cam1_match and cam2_match:
                mp1 = int(cam1_match.group(1))
                mp2 = int(cam2_match.group(1))

                if mp1 > mp2:
                    response += f"{phone1.get('model_name')} has a better camera ({mp1}MP vs {mp2}MP) and is recommended for photography."
                elif mp2 > mp1:
                    response += f"{phone2.get('model_name')} has a better camera ({mp2}MP vs {mp1}MP) and is recommended for photography."
                else:
                    response += f"Both phones have similar camera capabilities. Consider other factors like price and features."
        elif focus == 'battery':
            bat1_match = re.search(r'(\d+)\s*mAh', phone1.get('battery', ''))
            bat2_match = re.search(r'(\d+)\s*mAh', phone2.get('battery', ''))

            if bat1_match and bat2_match:
                mah1 = int(bat1_match.group(1))
                mah2 = int(bat2_match.group(1))

                if mah1 > mah2:
                    response += f"{phone1.get('model_name')} has better battery life ({mah1}mAh vs {mah2}mAh)."
                elif mah2 > mah1:
                    response += f"{phone2.get('model_name')} has better battery life ({mah2}mAh vs {mah1}mAh)."
                else:
                    response += f"Both phones have similar battery capacity."
        else:
            # General recommendation - newer phone usually better
            response += f"{phone1.get('model_name')} is the newer model with improved overall performance and features."

        return response

    def _generate_recommendation_review(self, extracted_data: dict) -> str:
        """Generate recommendation-focused response"""
        rec_data = extracted_data.get('recommendation_data', {})
        criteria = extracted_data.get('criteria', {})

        top_picks = rec_data.get('top_picks', extracted_data.get('phones', [])[:3])

        if not top_picks:
            return "I couldn't find phones matching your criteria."

        focus = criteria.get('focus', 'overall')
        price_max = criteria.get('price_max')

        response = "Based on your requirements, here are my recommendations:\n\n"

        if price_max:
            response = f"Best Samsung phones under ${int(price_max)}:\n\n"

        if focus == 'battery':
            response = "Best Samsung phones for battery life:\n\n"
        elif focus == 'camera':
            response = "Best Samsung phones for photography:\n\n"

        for i, phone in enumerate(top_picks[:3], 1):
            response += f"{i}. **{phone.get('model_name')}**\n"
            response += f"   • Price: {phone.get('price')}\n"
            response += f"   • Battery: {phone.get('battery')}\n"
            response += f"   • Camera: {phone.get('camera')}\n"
            response += f"   • Display: {phone.get('display')}\n\n"

        if top_picks:
            response += f"Top recommendation: {top_picks[0].get('model_name')} offers the best value for your needs."

        return response

    def _generate_general_review(self, extracted_data: dict) -> str:
        """Generate a general response"""
        phones = extracted_data.get('phones', [])

        if len(phones) == 1:
            return self._generate_specs_review(extracted_data)
        elif len(phones) >= 2:
            return self._generate_recommendation_review(extracted_data)
        else:
            return "Please ask about specific Samsung phone models or describe what you're looking for."


class MultiAgentSystem:
    """
    Orchestrates the multi-agent system
    Coordinates Data Extractor and Review Generator agents
    """

    def __init__(self):
        self.data_extractor = DataExtractorAgent()
        self.review_generator = ReviewGeneratorAgent()

    def process_query(self, query: str) -> str:
        """
        Process a user query through the multi-agent pipeline
        """
        # Step 1: Data Extractor pulls relevant data
        extracted_data = self.data_extractor.extract_data(query)

        # Step 2: Review Generator creates natural language response
        response = self.review_generator.generate_review(extracted_data)

        return response


# Singleton instance
_agent_system = None


def get_agent_system() -> MultiAgentSystem:
    global _agent_system
    if _agent_system is None:
        _agent_system = MultiAgentSystem()
    return _agent_system
