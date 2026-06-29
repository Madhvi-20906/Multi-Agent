import logging

logger = logging.getLogger(__name__)

def calculate_bakers_percentage(
    flour_weight: float,
    hydration_pct: float,
    salt_pct: float,
    yeast_pct: float
) -> str:
    """
    Computes precise ingredient weights based on standard Baker's Percentages,
    where all ingredient weights are calculated as a percentage of the total flour weight (100%).
    """
    logger.info(f"Executing Tool: calculate_bakers_percentage (flour={flour_weight}g, hydration={hydration_pct}%)")
    
    if flour_weight <= 0:
        return "Error: Flour weight must be greater than zero."
        
    water_weight = flour_weight * (hydration_pct / 100.0)
    salt_weight = flour_weight * (salt_pct / 100.0)
    yeast_weight = flour_weight * (yeast_pct / 100.0)
    total_weight = flour_weight + water_weight + salt_weight + yeast_weight
    
    summary = (
        f"### 🍞 Sourdough & Pastry Baker's Formula\n"
        f"Based on **{flour_weight:.1f}g** total flour weight (100% Benchmark):\n\n"
        f"| Ingredient | Baker's % | Weight (Grams) |\n"
        f"| :--- | :---: | :---: |\n"
        f"| **Flour** | 100.0% | **{flour_weight:.1f}g** |\n"
        f"| **Water (Hydration)** | {hydration_pct:.1f}% | **{water_weight:.1f}g** |\n"
        f"| **Salt** | {salt_pct:.1f}% | **{salt_weight:.1f}g** |\n"
        f"| **Yeast / Sourdough Starter** | {yeast_pct:.1f}% | **{yeast_weight:.1f}g** |\n\n"
        f"- **Total Yield Dough Weight:** **{total_weight:.1f}g**\n\n"
        f"> **Artisan Note:** *For high-hydration doughs (70%+), incorporate water slowly (autolyse) and use stretch-and-fold techniques during bulk fermentation to build strong gluten structure.*"
    )
    return summary

def adjust_rise_time(
    base_rise_hours: float,
    current_temp_f: float,
    target_temp_f: float
) -> str:
    """
    Heuristic to estimate fermentation/proofing duration adjustment based on kitchen temperature differences.
    Rule of thumb: Yeast activity roughly doubles for every 15°F (8.3°C) increase in temperature (up to ~105°F).
    """
    logger.info(f"Executing Tool: adjust_rise_time (base={base_rise_hours}h, current={current_temp_f}°F, target={target_temp_f}°F)")
    
    if base_rise_hours <= 0:
        return "Error: Base rise time must be greater than zero."
    if current_temp_f < 32 or target_temp_f < 32:
        return "Error: Temperatures must be above freezing."
    if current_temp_f > 115 or target_temp_f > 115:
        return "Warning: Yeast cells begin to die off at temperatures above 115°F. Adjustments might be inaccurate."
        
    # Heuristic adjustment factor
    # If target is hotter, rise time goes down
    diff = current_temp_f - target_temp_f
    factor = 2.0 ** (diff / 15.0)
    adjusted_time = base_rise_hours * factor
    
    summary = (
        f"### 🌡️ Fermentation & Proofing Adjustment\n"
        f"Adjusting proofing profile from **{current_temp_f:.1f}°F** to target **{target_temp_f:.1f}°F**:\n\n"
        f"- Base Fermentation Time: **{base_rise_hours:.1f} hours**\n"
        f"- Calculated Activity Scaling Factor: **{factor:.2f}x** speed\n"
        f"- **Adjusted Target Proofing Time:** **{adjusted_time:.2f} hours** ({int(adjusted_time * 60)} minutes)\n\n"
        f"> **Artisan Note:** *If proofing in a warmer kitchen, monitor bulk fermentation closely. Look for volume doubling, visible bubbling at the sides, and a slight dome shape to prevent over-proofing.*"
    )
    return summary
