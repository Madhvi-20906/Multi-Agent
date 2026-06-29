import json
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


def build_event_budget(
    event_type: str,
    guest_count: int,
    total_budget_usd: float,
    priority_categories: List[str],
    include_vendor_tips: bool = True
) -> str:
    """
    Generates a detailed event budget breakdown across all major spend categories
    based on event type, guest count, and total budget, weighted by user priorities.
    """
    base_allocations = {
        "wedding": {
            "venue": 0.30, "catering": 0.30, "photography": 0.12,
            "florals & decor": 0.10, "music & entertainment": 0.08,
            "attire & beauty": 0.07, "stationery & favors": 0.03
        },
        "birthday party": {
            "venue": 0.20, "catering & cake": 0.35, "entertainment": 0.20,
            "decor & florals": 0.12, "photography": 0.08, "invites & favors": 0.05
        },
        "corporate event": {
            "venue": 0.35, "catering": 0.28, "av & technology": 0.15,
            "speakers & talent": 0.12, "decor & branding": 0.06, "stationery & gifts": 0.04
        },
        "baby shower": {
            "venue": 0.15, "catering & cake": 0.30, "decor & florals": 0.25,
            "games & activities": 0.10, "photography": 0.10, "favors & stationery": 0.10
        },
        "anniversary dinner": {
            "venue & private dining": 0.40, "catering & wine": 0.35,
            "florals": 0.10, "photography": 0.08, "entertainment": 0.07
        },
        "graduation party": {
            "venue": 0.20, "catering": 0.35, "decor": 0.15,
            "entertainment": 0.15, "photography": 0.10, "favors": 0.05
        },
    }

    event_key = next((k for k in base_allocations if k in event_type.lower()), "birthday party")
    allocations = base_allocations[event_key].copy()

    # Boost priority categories by 20% and redistribute
    for cat in priority_categories:
        for key in allocations:
            if cat.lower() in key.lower():
                allocations[key] = min(allocations[key] * 1.20, 0.45)

    # Normalize to 1.0
    total = sum(allocations.values())
    allocations = {k: v / total for k, v in allocations.items()}

    per_person = total_budget_usd / guest_count if guest_count > 0 else 0

    line_items = {}
    for category, pct in allocations.items():
        amount = total_budget_usd * pct
        line_items[category] = {
            "percentage": f"{pct*100:.1f}%",
            "allocated_usd": f"${amount:,.0f}",
            "per_person_usd": f"${amount/guest_count:,.0f}" if guest_count > 0 else "N/A"
        }

    vendor_tips = {
        "venue": "Book 9-12 months in advance for popular venues. Ask about off-peak discounts (weekday/Sunday events).",
        "catering": "Family-style or buffet service reduces per-head costs vs. plated service. Always taste-test before signing.",
        "photography": "Ask about package bundles (photo + video). Review full galleries, not just highlight reels.",
        "florals & decor": "Use seasonal, locally sourced flowers to reduce cost by 30-40%. Greenery-forward arrangements are budget-friendly.",
        "music & entertainment": "Live bands cost 3-5x more than DJs. Consider a DJ with a live saxophonist for a hybrid experience.",
        "catering & cake": "Order a smaller show cake and sheet cakes for serving. Bakeries charge per slice, not per cake size.",
        "av & technology": "Get a dedicated AV coordinator — technical failures at corporate events are costly to your reputation.",
    }

    tips_output = {}
    if include_vendor_tips:
        for cat in allocations:
            for tip_key, tip_val in vendor_tips.items():
                if tip_key in cat.lower():
                    tips_output[cat] = tip_val

    result = {
        "event_type": event_type,
        "guest_count": guest_count,
        "total_budget": f"${total_budget_usd:,.0f}",
        "per_person_average": f"${per_person:,.0f}",
        "priority_categories": priority_categories,
        "budget_breakdown": line_items,
        "contingency_reserve": f"${total_budget_usd * 0.10:,.0f} (recommended 10% buffer)",
        "vendor_tips": tips_output,
        "pro_advice": [
            "Always get 3+ quotes per vendor before committing.",
            "Request itemised invoices — vague line items are a red flag.",
            "Pay deposits by credit card for consumer protection.",
            f"For {guest_count} guests, plan to confirm final headcount 2 weeks before the event.",
        ]
    }
    return json.dumps(result, indent=2)


def generate_event_timeline(
    event_type: str,
    event_date: str,
    venue_type: str,
    key_activities: List[str],
    start_time: str = "6:00 PM",
    duration_hours: float = 4.0
) -> str:
    """
    Generates a complete event day-of timeline with setup, reception,
    programme, and wrap-up phases — customised to the event type and activities.
    """
    pre_event_tasks = {
        "wedding": [
            "6 months prior: Book venue, photographer, caterer, officiant",
            "3 months prior: Send save-the-dates, finalise florals & music",
            "6 weeks prior: Send formal invitations, arrange accommodations",
            "2 weeks prior: Confirm all vendors, final guest count to caterer",
            "1 week prior: Rehearsal dinner, wedding party briefing",
            "Day before: Venue walkthrough, décor drop-off, early setup",
        ],
        "birthday party": [
            "4 weeks prior: Book venue and entertainment",
            "3 weeks prior: Send invitations",
            "1 week prior: Confirm catering and cake order",
            "2 days prior: Prepare decorations and party favors",
            "Day before: Balloon and banner setup if venue allows",
        ],
        "corporate event": [
            "3 months prior: Confirm venue, AV, and keynote speakers",
            "6 weeks prior: Send invitations and registration links",
            "3 weeks prior: Finalise programme and catering requirements",
            "1 week prior: Speaker briefing, AV dry-run",
            "Day before: Venue walkthrough, registration table prep",
        ],
    }

    event_key = next((k for k in pre_event_tasks if k in event_type.lower()), "birthday party")
    pre_tasks = pre_event_tasks[event_key]

    # Parse start time and generate schedule
    try:
        from datetime import datetime, timedelta
        base = datetime.strptime(start_time, "%I:%M %p")
    except Exception:
        try:
            from datetime import datetime, timedelta
            base = datetime.strptime(start_time, "%H:%M")
        except Exception:
            from datetime import datetime, timedelta
            base = datetime.strptime("6:00 PM", "%I:%M %p")

    schedule = []
    setup_start = base - __import__('datetime').timedelta(hours=2)
    schedule.append({"time": setup_start.strftime("%I:%M %p"), "activity": "Venue setup — florals, décor, tables, AV checks"})
    schedule.append({"time": (setup_start + __import__('datetime').timedelta(minutes=60)).strftime("%I:%M %p"), "activity": "Vendor arrivals — caterer, photographer, entertainment setup"})
    schedule.append({"time": (base - __import__('datetime').timedelta(minutes=30)).strftime("%I:%M %p"), "activity": "Host / wedding party arrival, final briefing"})
    schedule.append({"time": base.strftime("%I:%M %p"), "activity": "Doors open — guest arrival & welcome reception"})

    interval_minutes = int((duration_hours * 60) / max(len(key_activities), 1))
    current_time = base + __import__('datetime').timedelta(minutes=30)

    for activity in key_activities:
        schedule.append({"time": current_time.strftime("%I:%M %p"), "activity": activity})
        current_time += __import__('datetime').timedelta(minutes=interval_minutes)

    end_time = base + __import__('datetime').timedelta(hours=duration_hours)
    schedule.append({"time": end_time.strftime("%I:%M %p"), "activity": "Event close — thank guests, last dance / farewell toast"})
    schedule.append({"time": (end_time + __import__('datetime').timedelta(minutes=30)).strftime("%I:%M %p"), "activity": "Vendor breakdown — décor pack-up, venue clear-out"})

    result = {
        "event_type": event_type,
        "event_date": event_date,
        "venue_type": venue_type,
        "start_time": start_time,
        "estimated_end_time": end_time.strftime("%I:%M %p"),
        "duration_hours": duration_hours,
        "pre_event_planning_checklist": pre_tasks,
        "day_of_timeline": schedule,
        "coordinator_tips": [
            "Assign a dedicated point-of-contact for each vendor on the day.",
            "Build in 15-minute buffer slots between key programme items.",
            "Keep an emergency kit: safety pins, stain remover, pain reliever, phone chargers.",
            "Do a venue walkthrough 90 minutes before doors open.",
            "Designate one trusted person to manage vendor payments and tips on the day.",
        ]
    }
    return json.dumps(result, indent=2)
