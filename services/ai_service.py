from langchain_groq import ChatGroq
from langchain.schema import HumanMessage, AIMessage, SystemMessage
from core.config import get_settings
from typing import Optional
import httpx
import re
import json

settings = get_settings()

# In-memory session store
_sessions: dict = {}


def get_llm() -> ChatGroq:
    return ChatGroq(
        groq_api_key=settings.groq_api_key,
        model_name=settings.groq_model,
        temperature=0.4,
        max_tokens=512,
        http_client=httpx.Client(
            timeout=60.0,
            verify=False,
        ),
    )


def build_system_prompt(clinic_name: str, doctors_text: str, tests_text: str) -> str:
    return f"""You are HealthBot, a friendly and professional AI receptionist for {clinic_name}.

Your job is to:
1. Answer questions about our doctors, timings, and fees.
2. Answer questions about lab tests and their fees.
3. Help patients book appointments with doctors or schedule lab tests.

CLINIC INFORMATION:
━━━━━━━━━━━━━━━━━
AVAILABLE DOCTORS:
{doctors_text}

AVAILABLE LAB TESTS:
{tests_text}
━━━━━━━━━━━━━━━━━

BOOKING RULES (CRITICAL — follow exactly):
- When a patient wants to book, collect:
  1. Their full name
  2. Their WhatsApp phone number (for confirmation)
  3. Preferred date (format: YYYY-MM-DD)
  4. Which doctor OR which lab test they want
- Collect ONE piece of information per message. Be friendly and conversational.
- After collecting all 4 pieces, output EXACTLY this JSON on a new line (no other text after):
  BOOKING_REQUEST:{{"patient_name": "...", "phone": "...", "date": "YYYY-MM-DD", "booking_type": "doctor|lab_test", "doctor_id": "...|null", "test_id": "...|null"}}
- Use ONLY the doctor_id or test_id values provided in the clinic information above.
- If a patient asks for a doctor or test not in the list, politely say it's not available.
- If they provide a date in the past, ask for a future date.

PERSONALITY:
- Be warm, professional, and concise.
- Use emojis sparingly (1-2 per message max).
- Always respond in the same language the patient uses.
- Never make up information. Only use data provided above.
"""


def get_or_create_session(session_id: str, clinic_id: str) -> dict:
    if session_id not in _sessions:
        _sessions[session_id] = {
            "clinic_id": clinic_id,
            "history": [],
        }
    return _sessions[session_id]


def extract_booking_request(text: str) -> Optional[dict]:
    match = re.search(r"BOOKING_REQUEST:(\{.*?\})", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            return None
    return None


def clean_ai_response(text: str) -> str:
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

    # Last 20 messages history
    for msg in session["history"][-20:]:
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        else:
            messages.append(AIMessage(content=msg["content"]))

    messages.append(HumanMessage(content=user_message))

    response = await llm.ainvoke(messages)
    ai_text = response.content

    booking_request = extract_booking_request(ai_text)
    clean_reply = clean_ai_response(ai_text)

    session["history"].append({"role": "user", "content": user_message})
    session["history"].append({"role": "assistant", "content": clean_reply})

    if len(session["history"]) > 40:
        session["history"] = session["history"][-40:]

    return {
        "reply": clean_reply,
        "booking_request": booking_request,
    }


def clear_session(session_id: str):
    if session_id in _sessions:
        del _sessions[session_id]
