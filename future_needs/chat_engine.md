# dealer_ai/services/chat_engine.py

from .llm.factory import get_llm_provider
from .payment_engine import estimate_payment
from .inventory_search import search_inventory


SYSTEM_PROMPT = """
You are Dealer OS's AI Buying Assistant.

Your job:
- Help customers understand vehicles, payments, financing, and next steps.
- Be helpful, clear, and low-pressure.
- Never claim guaranteed approval.
- Never quote exact financing terms as final.
- Always explain that payments are estimates.
- If the customer wants unrealistic payments, educate them kindly.
- Recommend vehicles based on inventory and budget.
- When appropriate, ask if they want a salesperson to follow up.

Tone:
Friendly, honest, small-town dealership, not pushy.
"""


def build_chat_response(session, user_message):
    llm = get_llm_provider()

    vehicles = search_inventory(user_message)

    vehicle_context = "\n".join([
        f"- {v.year} {v.make} {v.model} {v.trim or ''}, "
        f"${v.price}, {v.mileage or 0} miles, stock #{v.stock_number}"
        for v in vehicles[:5]
    ])

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "system",
            "content": f"Relevant inventory:\n{vehicle_context or 'No matching inventory found.'}"
        },
    ]

    for msg in session.messages.order_by("created_at")[:20]:
        messages.append({
            "role": msg.role,
            "content": msg.content,
        })

    messages.append({"role": "user", "content": user_message})

    reply = llm.chat(messages)

    return {
        "reply": reply,
        "vehicles": [
            {
                "id": v.id,
                "stock_number": v.stock_number,
                "year": v.year,
                "make": v.make,
                "model": v.model,
                "trim": v.trim,
                "price": str(v.price),
                "url": v.url,
                "image_url": v.image_url,
            }
            for v in vehicles[:5]
        ]
    }