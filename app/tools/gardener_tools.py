import logging
from typing import List

logger = logging.getLogger(__name__)

def diagnose_plant(
    plant_type: str,
    symptoms: List[str],
    sun_exposure: str
) -> str:
    """
    Diagnoses plant health symptoms (e.g. yellow leaves, brown spots, wilting) and provides actionable organic remedies.
    """
    logger.info(f"Executing Tool: diagnose_plant (type={plant_type}, symptoms={symptoms})")
    
    # Normalize inputs
    cleaned_symptoms = [s.lower() for s in symptoms]
    plant_normalized = plant_type.lower()
    sun_normalized = sun_exposure.lower()
    
    primary_cause = "General stress / Undetermined factor"
    organic_remedies = []
    care_precautions = []
    
    # Simple diagnostic heuristics
    has_yellow = any("yellow" in s for s in cleaned_symptoms)
    has_brown = any("brown" in s or "spot" in s or "crisp" in s for s in cleaned_symptoms)
    has_wilt = any("wilt" in s or "droop" in s for s in cleaned_symptoms)
    has_white = any("white" in s or "powder" in s or "web" in s for s in cleaned_symptoms)
    
    if has_yellow:
        if "watering" in sun_normalized or "over" in cleaned_symptoms or "wet" in cleaned_symptoms:
            primary_cause = "Root Suffocation (Overwatering)"
            organic_remedies = [
                "Allow soil to dry out completely before next watering.",
                "Ensure container drainage holes are clear and functional."
            ]
        else:
            primary_cause = "Nitrogen Deficiency or Overwatering"
            organic_remedies = [
                "Amend soil with an organic liquid seaweed fertilizer or compost tea.",
                "Let top 2 inches of soil dry out between waterings."
            ]
        care_precautions = ["Avoid watering on strict calendar frequencies; always test soil dampness first."]
        
    elif has_brown:
        primary_cause = "Low Humidity or Scorch/Underwatering"
        organic_remedies = [
            "Increase local relative humidity with a pebbles water tray.",
            "Water deeply until water exits from container bottom drainage."
        ]
        if "direct" in sun_normalized or "hot" in sun_normalized:
            primary_cause = "Leaf Scorch / Excess Direct Solar Radiation"
            organic_remedies.append("Relocate plant to a filtered bright indirect light location.")
        care_precautions = ["Prune dead brown tips with sterilized shears to focus plant energy on healthy leaves."]
        
    elif has_wilt:
        primary_cause = "Underwatering or Root Rot"
        organic_remedies = [
            "Perform a deep soil flush or bottom watering.",
            "Inspect root system: if mushy/brown, prune infected roots and repot in fresh aerated soil."
        ]
        care_precautions = ["Ensure soil mix contains sufficient aeration elements like perlite or pumice."]
        
    elif has_white:
        primary_cause = "Powdery Mildew (Fungal Infection) or Spider Mites"
        organic_remedies = [
            "Apply organic neem oil solution or horticultural soap spray in evenings.",
            "Improve air circulation surrounding foliage stems."
        ]
        care_precautions = ["Avoid wetting foliage directly during morning or evening watering routines."]
        
    else:
        # Fallback diagnosis
        primary_cause = "Light or Nutrient Instability"
        organic_remedies = [
            "Verify plant's species light criteria (indirect vs direct sunlight).",
            "Feed with generic slow-release organic NPK fertilizer granules."
        ]
        care_precautions = ["Keep away from cooling/heating air vent drafts."]

    summary = (
        f"### 🌿 Botany Health Diagnostics Card\n"
        f"**Subject:** {plant_type.title()} | **Light Intake:** {sun_exposure.title()}\n\n"
        f"- **Primary Diagnosis:** **{primary_cause}**\n"
        f"- **Symptoms Analyzed:** {', '.join(symptoms)}\n\n"
        f"#### 🛠️ Recommended Care Adjustments & Organic Remedies:\n"
        + "\n".join([f"- {r}" for r in organic_remedies]) + "\n\n"
        f"#### ⚠️ Preventive Botanical Safeguards:\n"
        + "\n".join([f"- {p}" for p in care_precautions]) + "\n\n"
        f"> **Flora's Wisdom:** *Plants speak through their leaves. Keep soil aeration high and drainage clear to ensure strong root system oxygenation.*"
    )
    return summary

def generate_watering_schedule(
    plant_type: str,
    container_type: str,
    climate: str,
    soil_type: str
) -> str:
    """
    Formulates a customized watering frequency recommendation based on container, climate, and soil variables.
    """
    logger.info(f"Executing Tool: generate_watering_schedule (plant={plant_type}, container={container_type}, climate={climate})")
    
    p_type = plant_type.lower()
    c_type = container_type.lower()
    clim = climate.lower()
    soil = soil_type.lower()
    
    # Calculate watering intervals (days)
    base_interval = 7
    
    # Plant category adjustment
    if "succulent" in p_type or "cactus" in p_type or "snake" in p_type or "aloe" in p_type:
        base_interval += 7
    elif "tropical" in p_type or "fern" in p_type or "ficus" in p_type:
        base_interval -= 3
    elif "veggie" in p_type or "tomato" in p_type or "herb" in p_type:
        base_interval -= 4
        
    # Container porous factor
    if "terracotta" in c_type or "clay" in c_type:
        base_interval -= 1  # Dries faster
    elif "plastic" in c_type or "glaze" in c_type:
        base_interval += 1  # Retains water
        
    # Climate factor
    if "hot" in clim or "arid" in clim or "dry" in clim:
        base_interval -= 2
    elif "cool" in clim or "humid" in clim:
        base_interval += 2
        
    # Soil drainage factor
    if "sandy" in soil or "cactus mix" in soil:
        base_interval -= 1  # Dries fast
    elif "clay" in soil or "heavy" in soil:
        base_interval += 2  # Dries very slow
        
    # Guard intervals
    final_interval = max(1, base_interval)
    
    summary = (
        f"### 💧 Personalized Botanical Watering Calendar\n"
        f"Configured for **{plant_type.title()}** in a **{container_type.title()}** container with **{soil_type.title()}** soil.\n\n"
        f"- **Primary Watering Cycle:** Water deeply every **{final_interval} days**.\n"
        f"- **Climate Influence:** adjusted for a **{climate.title()}** environment.\n"
        f"- **Estimated Water Volume:** saturating until bottom flow runs free, discarding excess tray water.\n\n"
        f"#### 📅 Weekly Care Calendar Checkpoints:\n"
        f"- **Active Days:** Every week on morning cycles.\n"
        f"- **Soil Test Trigger:** Insert finger 2 inches into soil. Water only if soil feels completely dry at that depth.\n\n"
        f"> **Flora's Wisdom:** *Under-watering is simple to remedy, but over-watering is often fatal. When in doubt, defer watering by 24-48 hours.*"
    )
    return summary
