import re
import logging
from typing import List, Dict, Any
from fractions import Fraction

logger = logging.getLogger(__name__)

def scale_ingredients(ingredients: List[str], scale_factor: float) -> str:
    """
    Scales a list of ingredients by a given multiplier (e.g. 2.0 to double, 0.5 to halve).
    Parses integers, fractions (like 1/2), and floats, and returns a formatted scaled list.
    """
    logger.info(f"Executing Tool: scale_ingredients with factor={scale_factor}")
    if scale_factor <= 0:
        return "Error: Scale factor must be greater than zero."
        
    scaled_list = []
    
    # Regex to match leading numbers (integers, decimals, or fractions)
    number_pattern = re.compile(r"^(\d+\s+\d+/\d+|\d+/\d+|\d+\.\d+|\d+)")
    
    for ing in ingredients:
        match = number_pattern.match(ing.strip())
        if match:
            num_str = match.group(1)
            remaining_text = ing.strip()[match.end():]
            
            try:
                # Parse fraction/decimal/integer
                if "/" in num_str:
                    if " " in num_str:
                        parts = num_str.split()
                        val = float(parts[0]) + float(Fraction(parts[1]))
                    else:
                        val = float(Fraction(num_str))
                else:
                    val = float(num_str)
                    
                new_val = val * scale_factor
                
                # Format output values cleanly
                if new_val.is_integer():
                    formatted_val = str(int(new_val))
                elif (new_val * 4).is_integer():
                    # Format as fractional representation (e.g., 0.25 -> 1/4, 1.5 -> 1 1/2)
                    whole = int(new_val)
                    frac = new_val - whole
                    if whole > 0:
                        formatted_val = f"{whole} {Fraction(frac).limit_denominator()}"
                    else:
                        formatted_val = f"{Fraction(frac).limit_denominator()}"
                else:
                    formatted_val = f"{new_val:.2f}".rstrip('0').rstrip('.')
                    
                scaled_list.append(f"{formatted_val}{remaining_text}")
            except Exception as e:
                logger.error(f"Error parsing quantity in ingredient '{ing}': {e}")
                scaled_list.append(f"{ing} (scaled by {scale_factor}x)")
        else:
            scaled_list.append(f"{ing} (scaled by {scale_factor}x)")
            
    result = f"### Scaled Ingredient List ({scale_factor}x Portion Size)\n"
    result += "\n".join([f"- {item}" for item in scaled_list])
    return result


def convert_units(amount: float, from_unit: str, to_unit: str) -> str:
    """
    Converts measurements between popular metric and imperial culinary units.
    Supported: grams (g) <-> ounces (oz), cups <-> milliliters (ml), tablespoons (tbsp) <-> teaspoons (tsp).
    """
    logger.info(f"Executing Tool: convert_units of {amount} from {from_unit} to {to_unit}")
    u_from = from_unit.strip().lower()
    u_to = to_unit.strip().lower()
    
    conversions = {
        ("g", "oz"): amount * 0.035274,
        ("oz", "g"): amount * 28.3495,
        ("cups", "ml"): amount * 236.588,
        ("cup", "ml"): amount * 236.588,
        ("ml", "cups"): amount / 236.588,
        ("ml", "cup"): amount / 236.588,
        ("tbsp", "tsp"): amount * 3.0,
        ("tsp", "tbsp"): amount / 3.0,
        ("tbsp", "ml"): amount * 14.7868,
        ("ml", "tbsp"): amount / 14.7868,
        ("tsp", "ml"): amount * 4.92892,
        ("ml", "tsp"): amount / 4.92892,
    }
    
    key = (u_from, u_to)
    if key in conversions:
        converted = conversions[key]
        return f"**Unit Conversion Result:** {amount} {from_unit} = **{converted:.2f} {to_unit}**"
    else:
        return f"Error: Conversion from '{from_unit}' to '{to_unit}' is currently unsupported."


def estimate_nutrition(ingredients: List[str]) -> str:
    """
    Approximates nutrition profiles (Calories, Protein, Carbohydrates, Fats) based on list keywords.
    Provides healthy culinary estimates without requiring heavy API call payloads.
    """
    logger.info("Executing Tool: estimate_nutrition")
    
    total_cal = 0
    total_protein = 0
    total_carbs = 0
    total_fat = 0
    
    # Very basic token heuristic database for dynamic estimates
    heuristics = {
        "beef": {"cal": 250, "p": 26, "c": 0, "f": 17},
        "steak": {"cal": 250, "p": 26, "c": 0, "f": 17},
        "chicken": {"cal": 165, "p": 31, "c": 0, "f": 3.6},
        "tofu": {"cal": 80, "p": 8, "c": 2, "f": 5},
        "almond flour": {"cal": 160, "p": 6, "c": 6, "f": 14},
        "egg": {"cal": 70, "p": 6, "c": 0.6, "f": 5},
        "butter": {"cal": 100, "p": 0, "c": 0, "f": 11},
        "oil": {"cal": 120, "p": 0, "c": 0, "f": 14},
        "cheese": {"cal": 110, "p": 7, "c": 1, "f": 9},
        "mozzarella": {"cal": 85, "p": 6, "c": 1, "f": 6},
        "avocado": {"cal": 160, "p": 2, "c": 9, "f": 15},
        "broccoli": {"cal": 30, "p": 2.5, "c": 6, "f": 0.3},
        "rice": {"cal": 130, "p": 2.7, "c": 28, "f": 0.3},
    }
    
    number_pattern = re.compile(r"^(\d+\s+\d+/\d+|\d+/\d+|\d+\.\d+|\d+)")
    
    for ing in ingredients:
        cleaned = ing.lower()
        matched_heuristics = []
        
        # Check matching food keys
        for key, macros in heuristics.items():
            if key in cleaned:
                matched_heuristics.append(macros)
                
        # Parse quantity multiplier if available
        multiplier = 1.0
        match = number_pattern.match(ing.strip())
        if match:
            try:
                num_str = match.group(1)
                if "/" in num_str:
                    if " " in num_str:
                        parts = num_str.split()
                        multiplier = float(parts[0]) + float(Fraction(parts[1]))
                    else:
                        multiplier = float(Fraction(num_str))
                else:
                    multiplier = float(num_str)
            except:
                multiplier = 1.0
                
        # Aggregate macros (using heuristics normalized roughly per unit)
        if matched_heuristics:
            # Average out if multiple keywords matched
            avg_cal = sum(m["cal"] for m in matched_heuristics) / len(matched_heuristics)
            avg_p = sum(m["p"] for m in matched_heuristics) / len(matched_heuristics)
            avg_c = sum(m["c"] for m in matched_heuristics) / len(matched_heuristics)
            avg_f = sum(m["f"] for m in matched_heuristics) / len(matched_heuristics)
            
            total_cal += avg_cal * multiplier
            total_protein += avg_p * multiplier
            total_carbs += avg_c * multiplier
            total_fat += avg_f * multiplier
        else:
            # default fallback item (low calorie veggies/spices)
            total_cal += 15 * multiplier
            total_carbs += 3 * multiplier
            
    summary = (
        f"### Estimated Macro-Nutritional Profile\n"
        f"*Values are approximated based on recipe ingredient list:*\n\n"
        f"- **Calories:** ~{int(total_cal)} kcal\n"
        f"- **Protein:** ~{total_protein:.1f} g\n"
        f"- **Total Fats:** ~{total_fat:.1f} g\n"
        f"- **Carbohydrates:** ~{total_carbs:.1f} g\n\n"
        f"> *Note: These are quick algorithmic estimations. Use an official USDA nutrition database for strict dietary metrics.*"
    )
    return summary
