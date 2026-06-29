import json
import logging
from typing import List

logger = logging.getLogger(__name__)


def build_outfit(
    occasion: str,
    style_preference: str,
    body_type: str,
    season: str,
    color_palette: List[str]
) -> str:
    """
    Generates a complete styled outfit recommendation for a given occasion,
    style preference, body type, season, and color palette.
    """
    season_fabrics = {
        "spring": ["linen", "light cotton", "chambray", "jersey"],
        "summer": ["breathable linen", "lightweight cotton", "silk chiffon", "moisture-wicking jersey"],
        "autumn": ["wool", "tweed", "corduroy", "brushed cotton", "flannel"],
        "winter": ["cashmere", "thick wool", "velvet", "fleece-lined knit", "heavy denim"],
    }
    fabrics = season_fabrics.get(season.lower(), ["cotton", "linen"])

    body_tips = {
        "hourglass": "Emphasise your waist with belted pieces, wrap dresses, and fitted silhouettes.",
        "pear": "Balance proportions with wide-leg trousers, A-line skirts, and statement tops.",
        "apple": "Create definition with V-necks, empire-waist tops, and fluid wide-leg pants.",
        "rectangle": "Add curves with peplum tops, ruffled details, and high-waisted bottoms.",
        "inverted triangle": "Balance broad shoulders with wide-leg trousers, A-line skirts, and minimal shoulder detail.",
        "petite": "Elongate with monochromatic looks, vertical stripes, high-waisted cuts, and heels.",
        "tall": "Play with proportions using cropped tops, midi hemlines, and bold horizontal patterns.",
    }
    silhouette_tip = body_tips.get(body_type.lower(), "Wear what makes you feel confident and comfortable.")

    occasion_map = {
        "business formal": ("Tailored blazer + pressed trousers/pencil skirt", "Oxford shoes or block-heel pumps", "Structured leather tote"),
        "business casual": ("Smart chinos/midi skirt + a tucked blouse", "Loafers or ankle boots", "Crossbody or structured bag"),
        "cocktail party": ("Midi wrap dress or velvet blazer + wide-leg trousers", "Strappy heels or pointed-toe flats", "Clutch or mini bag"),
        "casual weekend": ("High-waisted jeans + relaxed knit top", "White sneakers or mules", "Canvas tote or backpack"),
        "date night": ("Fitted midi dress or elevated separates", "Block heels or Chelsea boots", "Small crossbody"),
        "gym / activewear": ("Moisture-wicking leggings + breathable sports top", "Performance trainers", "Gym duffel"),
        "beach / resort": ("Flowy sundress or linen co-ord set", "Sandals or espadrilles", "Straw tote"),
        "wedding guest": ("Floral midi dress or pastel suit", "Kitten heels or strappy sandals", "Small clutch"),
    }
    key = next((k for k in occasion_map if k in occasion.lower()), None)
    outfit_base, footwear, bag = occasion_map.get(key, ("Smart separates suited to the occasion", "Neutral versatile shoes", "Classic handbag"))

    colors_str = ", ".join(color_palette) if color_palette else "neutral tones (black, white, camel)"
    fabric_str = " or ".join(fabrics[:2])

    result = {
        "occasion": occasion,
        "season": season.capitalize(),
        "style_preference": style_preference,
        "body_type_tip": silhouette_tip,
        "outfit": {
            "core_pieces": outfit_base,
            "recommended_fabrics": fabric_str.capitalize(),
            "color_palette": colors_str,
            "footwear": footwear,
            "bag": bag,
        },
        "styling_notes": [
            f"Stick to your chosen palette ({colors_str}) for a cohesive, put-together look.",
            silhouette_tip,
            f"For {season.lower()}, opt for {fabric_str} to stay comfortable and stylish.",
            "Accessorise with one statement piece — bold earrings, a silk scarf, or a structured belt.",
            "Always prioritise fit: well-fitted basics always outperform poorly-fitted designer pieces.",
        ]
    }
    return json.dumps(result, indent=2)


def analyze_color_palette(
    skin_tone: str,
    hair_color: str,
    eye_color: str,
    preferred_mood: str
) -> str:
    """
    Analyzes personal coloring (skin, hair, eyes) to recommend a flattering
    wardrobe color palette aligned with the user's aesthetic mood.
    """
    season_palettes = {
        "warm spring": ["coral", "peach", "warm ivory", "golden yellow", "turquoise", "warm green", "camel"],
        "warm autumn": ["terracotta", "burnt orange", "olive green", "mustard", "rust", "chocolate brown", "cream"],
        "cool summer": ["dusty rose", "lavender", "powder blue", "slate grey", "soft white", "mauve", "sage green"],
        "cool winter": ["royal blue", "emerald", "true red", "fuchsia", "icy white", "deep plum", "charcoal black"],
    }

    warm_skin = ["golden", "olive", "warm beige", "honey", "tan", "bronze", "sallow", "peachy"]
    cool_skin = ["pink", "rosy", "cool beige", "porcelain", "ebony", "espresso", "neutral"]

    warm_hair = ["blonde", "auburn", "red", "chestnut", "golden brown", "copper"]
    cool_hair = ["ash blonde", "platinum", "jet black", "cool brown", "grey", "silver"]

    is_warm_skin = any(t in skin_tone.lower() for t in warm_skin)
    is_warm_hair = any(t in hair_color.lower() for t in warm_hair)

    if is_warm_skin or is_warm_hair:
        season_type = "warm autumn" if "deep" in skin_tone.lower() or "olive" in skin_tone.lower() else "warm spring"
    else:
        season_type = "cool winter" if "deep" in skin_tone.lower() or "dark" in skin_tone.lower() else "cool summer"

    palette = season_palettes[season_type]

    mood_accents = {
        "romantic": ["blush pink", "soft lilac", "champagne", "dusty rose"],
        "edgy": ["matte black", "cobalt", "fire red", "steel grey"],
        "minimalist": ["off-white", "stone grey", "warm taupe", "deep navy"],
        "bohemian": ["terracotta", "sage green", "burnt sienna", "cream"],
        "classic": ["navy", "camel", "crisp white", "burgundy"],
        "playful": ["sunshine yellow", "electric blue", "hot coral", "lime green"],
    }
    accent_colors = mood_accents.get(preferred_mood.lower(), ["neutral tones"])

    result = {
        "personal_color_season": season_type.title(),
        "skin_tone": skin_tone,
        "hair_color": hair_color,
        "eye_color": eye_color,
        "preferred_mood": preferred_mood,
        "foundation_palette": palette,
        "mood_accent_colors": accent_colors,
        "avoid_colors": ["muddy browns", "harsh neons clashing with undertone", "colours that dull the complexion"],
        "styling_principles": [
            f"Your {season_type.title()} coloring thrives in {', '.join(palette[:3])}.",
            f"For a {preferred_mood} aesthetic, accent with {', '.join(accent_colors[:2])}.",
            "Wear your best colours near your face — in tops, scarves, or statement necklines.",
            "Neutral wardrobe staples in your palette ensure easy mix-and-match outfits.",
            "When in doubt, a monochromatic look in your best neutrals is always elegant.",
        ]
    }
    return json.dumps(result, indent=2)
