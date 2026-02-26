"""
Chat Routes

POST /api/chat/{clinic_id}     → Standard HTTP chat endpoint (for chatbot widget)
WS   /ws/admin/{clinic_id}     → WebSocket for admin dashboard real-time updates
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Depends
from pydantic import BaseModel
from db.mongodb import get_db
from services import ai_service, clinic_service, booking_service, whatsapp_service
from websocket.manager import ws_manager
from core.dependencies import get_clinic_id_from_token
import uuid
from datetime import datetime

router = APIRouter(tags=["Chat"])


class ChatMessage(BaseModel):
    message: str
    session_id: str = ""  # Client generates and persists this


@router.post("/api/chat/{clinic_id}")
async def chat_endpoint(
    clinic_id: str,
    body: ChatMessage,
    db=Depends(get_db),
):
    """
    Main chatbot endpoint. Processes user message, returns AI reply.
    If AI detects booking intent, automatically books the appointment.
    """
    # Fetch clinic data
    clinic = await clinic_service.get_clinic_by_id(db, clinic_id)
    if not clinic or not clinic.get("is_active"):
        raise HTTPException(404, detail="Clinic not found")

    # Get context data for AI
    doctors = await clinic_service.get_doctors(db, clinic_id)
    tests = await clinic_service.get_lab_tests(db, clinic_id)
    doctors_text = clinic_service.format_doctors_for_ai(doctors)
    tests_text = clinic_service.format_tests_for_ai(tests)

    # Generate session_id if not provided
    session_id = body.session_id or str(uuid.uuid4())

    # Get AI response
    result = await ai_service.chat(
        session_id=session_id,
        clinic_id=clinic_id,
        user_message=body.message,
        clinic_name=clinic["name"],
        doctors_text=doctors_text,
        tests_text=tests_text,
    )

    response_data = {
        "reply": result["reply"],
        "session_id": session_id,
        "booking_confirmed": None,
    }

    # ── Handle booking request if AI extracted one ────────────────────────────
    if result["booking_request"]:
        br = result["booking_request"]
        settings_data = clinic.get("settings", {})

        # Get doctor or test details
        fee = 0.0
        doctor_name = None
        test_name = None

        if br.get("booking_type") == "doctor" and br.get("doctor_id"):
            doctor = await clinic_service.get_doctor_by_id(db, clinic_id, br["doctor_id"])
            if doctor:
                fee = doctor["consultation_fee"]
                doctor_name = doctor["name"]

        elif br.get("booking_type") == "lab_test" and br.get("test_id"):
            test = await clinic_service.get_lab_test_by_id(db, clinic_id, br["test_id"])
            if test:
                fee = test["fee"]
                test_name = test["name"]

        # Assign slot
        time_slot, actual_date = await booking_service.assign_next_available_slot(
            db=db,
            clinic_id=clinic_id,
            requested_date=br["date"],
            max_patients=settings_data.get("max_patients_per_day", 50),
            slot_minutes=settings_data.get("slot_duration_minutes", 10),
            working_start=settings_data.get("working_hours_start", "09:00"),
            working_end=settings_data.get("working_hours_end", "17:00"),
        )

        if not time_slot:
            return {
                **response_data,
                "reply": result["reply"] + "\n\n⚠️ Sorry, no available slots in the next 30 days. Please call the clinic directly.",
            }

        # Build appointment document
        appointment = {
            "appointment_id": str(uuid.uuid4()),
            "clinic_id": clinic_id,
            "patient_name": br["patient_name"],
            "phone": br["phone"],
            "date": actual_date,
            "time_slot": time_slot,
            "booking_type": br["booking_type"],
            "doctor_id": br.get("doctor_id"),
            "doctor_name": doctor_name,
            "test_id": br.get("test_id"),
            "test_name": test_name,
            "fee": fee,
            "status": "confirmed",
            "whatsapp_sent": False,
            "notes": "",
            "created_at": datetime.utcnow().isoformat(),
        }

        # Save to MongoDB
        await booking_service.create_appointment(db, appointment)

        # Send WhatsApp notification (non-blocking)
        wa_sent = await whatsapp_service.send_whatsapp_notification(appointment, clinic["name"])
        if wa_sent:
            await db["appointments"].update_one(
                {"appointment_id": appointment["appointment_id"]},
                {"$set": {"whatsapp_sent": True}}
            )

        # Broadcast to admin dashboard via WebSocket
        await ws_manager.broadcast_to_clinic(
            clinic_id=clinic_id,
            event_type="new_appointment",
            data={
                **appointment,
                "whatsapp_sent": wa_sent,
                "clinic_name": clinic["name"],
            }
        )

        # Slot note if date was shifted
        date_note = ""
        if actual_date != br["date"]:
            date_note = f"\n\n📅 Note: Your requested date was fully booked, so I've scheduled you for {actual_date} instead."

        response_data["reply"] = (
            f"✅ Your appointment has been confirmed!\n\n"
            f"📋 **Booking Summary:**\n"
            f"👤 Name: {appointment['patient_name']}\n"
            f"📅 Date: {actual_date}\n"
            f"⏰ Time: {time_slot}\n"
            f"💊 {'Dr. ' + doctor_name if doctor_name else test_name}\n"
            f"💰 Fee: PKR {fee:.0f}\n"
            f"🆔 ID: {appointment['appointment_id'][:8].upper()}"
            f"{date_note}\n\n"
            f"{'📱 A WhatsApp confirmation has been sent to your number.' if wa_sent else '📞 Please save your booking ID.'}"
        )
        response_data["booking_confirmed"] = appointment

    return response_data


@router.websocket("/ws/admin/{clinic_id}")
async def admin_websocket(websocket: WebSocket, clinic_id: str, db=Depends(get_db)):
    """
    WebSocket endpoint for admin dashboard real-time updates.
    Admins connect here to receive instant appointment notifications.
    """
    await ws_manager.connect(websocket, clinic_id)
    try:
        # Send initial connection confirmation
        await ws_manager.send_personal_message(websocket, "connected", {
            "clinic_id": clinic_id,
            "message": "Dashboard connected. Listening for appointments...",
        })

        # Keep connection alive — ping/pong
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text('{"event":"pong","data":{}}')

    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, clinic_id)
