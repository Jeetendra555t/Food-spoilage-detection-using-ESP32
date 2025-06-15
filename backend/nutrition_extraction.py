from transformers import pipeline
import re
from typing import Dict, List, Union, Optional

def normalize_unit(value: str) -> float:
    """Convert various unit formats to standard values"""
    value = value.lower().strip()
    # Remove any non-numeric characters except decimal point
    numeric = re.sub(r'[^\d.]', '', value)
    if not numeric:
        return 0.0
    
    # Convert to float
    result = float(numeric)
    
    # Handle different units
    if 'mg' in value:
        if 'g' in value:  # e.g., "1.5g (1500mg)"
            return result
        return result / 1000  # Convert mg to g
    elif 'mcg' in value or 'μg' in value:
        return result / 1000000  # Convert mcg to g
    elif 'kg' in value:
        return result * 1000  # Convert kg to g
    return result

def extract_nutrition(text: str) -> Dict[str, Union[float, str, List[str]]]:
    """Extract nutrition information from text using improved pattern matching"""
    
    def get_value(label: str, default: float = 0.0) -> float:
        # Try different patterns for the label
        patterns = [
            rf'{label}[:\s]*([\d.,]+)\s*(?:g|mg|mcg|μg|kg)?',  # Standard format
            rf'{label}\s*=\s*([\d.,]+)\s*(?:g|mg|mcg|μg|kg)?',  # With equals sign
            rf'{label}\s*\(([\d.,]+)\s*(?:g|mg|mcg|μg|kg)?\)',  # In parentheses
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return normalize_unit(match.group(1))
        return default

    def get_ingredients() -> List[str]:
        # Look for ingredients section
        patterns = [
            r'ingredients[:\s]*([^.]*?)(?:\.|$)',  # Until period or end
            r'contains[:\s]*([^.]*?)(?:\.|$)',     # Alternative format
            r'ingredients[:\s]*([^;]*?)(?:;|$)',   # Until semicolon or end
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                # Split by common separators and clean up
                ingredients = re.split(r'[,;]', match.group(1))
                return [i.strip() for i in ingredients if i.strip()]
        return []

    def get_serving_size() -> str:
        patterns = [
            r'serving size[:\s]*([^.]*?)(?:\.|$)',
            r'serving[:\s]*([^.]*?)(?:\.|$)',
            r'per serving[:\s]*([^.]*?)(?:\.|$)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return ''

    def calculate_health_score(nutrition: Dict[str, Union[float, str, List[str]]]) -> float:
        score = 10.0
        calories = nutrition.get('calories', 0)
        protein = nutrition.get('protein', 0)
        carbs = nutrition.get('carbs', 0)
        fat = nutrition.get('fat', 0)
        fiber = nutrition.get('fiber', 0)
        sugar = nutrition.get('sugar', 0)
        sodium = nutrition.get('sodium', 0)
        
        # Calorie scoring (0-2000 is ideal)
        if calories > 2000:
            score -= (calories - 2000) / 500
        
        # Protein scoring (higher is better, up to 50g)
        protein_score = min(protein / 50, 1)
        score += protein_score
        
        # Carb scoring (lower is better, up to 300g)
        if carbs > 300:
            score -= (carbs - 300) / 100
        
        # Fat scoring (lower is better, up to 70g)
        if fat > 70:
            score -= (fat - 70) / 35
        
        # Fiber scoring (higher is better, up to 25g)
        fiber_score = min(fiber / 25, 1)
        score += fiber_score
        
        # Sugar scoring (lower is better, up to 50g)
        if sugar > 50:
            score -= (sugar - 50) / 25
        
        # Sodium scoring (lower is better, up to 2300mg)
        if sodium > 2300:
            score -= (sodium - 2300) / 1150
        
        # Ensure score is between 0 and 10
        return max(0, min(10, score))

    def get_warnings_and_benefits(nutrition: Dict[str, Union[float, str, List[str]]]) -> tuple[List[str], List[str]]:
        warnings = []
        benefits = []
        
        # Check for high values
        if nutrition.get('sodium', 0) > 2300:
            warnings.append('High in sodium')
        if nutrition.get('sugar', 0) > 50:
            warnings.append('High in sugar')
        if nutrition.get('fat', 0) > 70:
            warnings.append('High in fat')
        if nutrition.get('calories', 0) > 2000:
            warnings.append('High in calories')
            
        # Check for beneficial values
        if nutrition.get('protein', 0) > 20:
            benefits.append('High in protein')
        if nutrition.get('fiber', 0) > 10:
            benefits.append('High in fiber')
        if nutrition.get('sugar', 0) < 10:
            benefits.append('Low in sugar')
        if nutrition.get('sodium', 0) < 500:
            benefits.append('Low in sodium')
            
        return warnings, benefits

    # Extract basic nutrition values
    nutrition = {
        'calories': get_value('calories'),
        'protein': get_value('protein'),
        'carbs': get_value('carb|carbohydrate'),
        'fat': get_value('fat'),
        'fiber': get_value('fiber'),
        'sugar': get_value('sugar'),
        'sodium': get_value('sodium'),
        'ingredients': get_ingredients(),
        'serving_size': get_serving_size(),
    }
    
    # Calculate health score
    nutrition['health_score'] = calculate_health_score(nutrition)
    
    # Get warnings and benefits
    warnings, benefits = get_warnings_and_benefits(nutrition)
    nutrition['warnings'] = warnings
    nutrition['benefits'] = benefits
    
    return nutrition 