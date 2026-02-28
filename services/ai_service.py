from langchain_groq import ChatGroq
from langchain.schema import HumanMessage, AIMessage, SystemMessage
from core.config import get_settings
from typing import Optional
import httpx
import re
import json
from datetime import date

settings = get_settings()

# In-memory session store
_sessions: dict = {}


def get_llm() -> ChatGroq:
    return ChatGroq(
        groq_api_key=settings.groq_api_key,
        model_name=settings.groq_model,
        temperature=0.3,
        max_tokens=600,
        http_client=httpx.Client(
            timeout=60.0,
            verify=False,
        ),
    )


def build_system_prompt(clinic_name: str, doctors_text: str, tests_text: str) -> str:
    today_str = date.today().strftime("%Y-%m-%d")
    today_day = date.today().strftime("%A")

    return f"""You are HealthBot, a friendly AI receptionist for {clinic_name}.

TODAY'S DATE: {today_str} ({today_day})
Use this as default date if patient says "today", "aaj", or doesn't specify a date.

CLINIC INFORMATION:
━━━━━━━━━━━━━━━━━
AVAILABLE DOCTORS (use exact ID in booking):
{doctors_text}

AVAILABLE LAB TESTS (use exact ID in booking):
{tests_text}
━━━━━━━━━━━━━━━━━

YOUR JOB:
1. Answer questions about doctors, timings, fees.
2. Answer questions about lab tests and fees.
3. Help patients book appointments.

BOOKING STEPS — collect in order:
1. Patient's full name
2. WhatsApp phone number
3. Preferred date (use {today_str} if they say "aaj/today/now/abhi")
4. Which doctor OR which lab test

CRITICAL RULES:
- Collect ONE piece of info per message.
- Use EXACT doctor_id or test_id from the list above — NEVER make up IDs.
- When you have ALL 4 pieces, output this JSON on its own line at the END:
  BOOKING_REQUEST:{{"patient_name": "Full Name", "phone": "03001234567", "date": "YYYY-MM-DD", "booking_type": "doctor", "doctor_id": "EXACT-ID-FROM-LIST", "test_id": null}}
  OR for lab test:
  BOOKING_REQUEST:{{"patient_name": "Full Name", "phone": "03001234567", "date": "YYYY-MM-DD", "booking_type": "lab_test", "doctor_id": null, "test_id": "EXACT-ID-FROM-LIST"}}
- Date format MUST be YYYY-MM-DD.
- Today's date is {today_str} — bookings for today ARE allowed.
- Do NOT output BOOKING_REQUEST until you have all 4 pieces.
- After outputting BOOKING_REQUEST, stop — do not add more text.

PERSONALITY:
- Warm, professional, concise.
- Reply in the same language as the patient (Urdu/English).
- Use 1-2 emojis max per message.
- Never make up information.
"""


def get_or_create_session(session_id: str, clinic_id: str) -> dict:
    if session_id not in _sessions:
        _sessions[session_id] = {
            "clinic_id": clinic_id,
            "history": [],
        }
    return _sessions[session_id]


def extract_booking_request(text: str) -> Optional[dict]:
    """Extract BOOKING_REQUEST JSON from AI response."""
    match = re.search(r"BOOKING_REQUEST:(\{.*?\})", text, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(1))
            # Validate required fields
            if data.get("patient_name") and data.get("phone") and data.get("date"):
                # Fix date if AI gave wrong format
                d = data.get("date", "")
                if d and len(d) == 10 and d[4] == "-":
                    return data
                else:
                    # Try to fix date
                    data["date"] = date.today().strftime("%Y-%m-%d")
                    return data
        except json.JSONDecodeError:
            return None
    return None


def clean_ai_response(text: str) -> str:
    """Remove BOOKING_REQUEST JSON from visible response."""
    return re.sub(r"\nBOOKING_REQUEST:\{.*?\}", "", text, flags=re.DOTALL).strip()


async def chat(
    session_id: str,
    clinic_id: str,
    user_message: str,
    clinic_name: str,
    doctors_text: str,
    tests_text: str,
) -> dict:
    session = get_or_create_session(session_id, clinic_id)
    llm = get_llm()

    system_prompt = build_system_prompt(clinic_name, doctors_text, tests_text)

    messages = [SystemMessage(content=system_prompt)]
    for msg in session["history"][-10:]:  # Last 10 messages for context
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        else:
            messages.append(AIMessage(content=msg["content"]))
    messages.append(HumanMessage(content=user_message))

    try:
        response = await llm.ainvoke(messages)
        ai_text = response.content

        # Extract booking request if present
        booking_request = extract_booking_request(ai_text)
        clean_response = clean_ai_response(ai_text)

        # Save to history
        session["history"].append({"role": "user", "content": user_message})
        session["history"].append({"role": "assistant", "content": clean_response})

        return {
            "reply": clean_response,
            "booking_request": booking_request,
        }

    except Exception as e:
        return {
            "reply": "I'm having trouble connecting right now. Please try again or call the clinic directly.",
            "booking_request": None,
        }
