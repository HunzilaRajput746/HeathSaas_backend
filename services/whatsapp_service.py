from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
from core.config import get_settings
import logging

logger = logging.getLogger(__name__)
settings = get_settings()


def format_phone_for_whatsapp(phone: str) -> str:
    """
    Normalize phone number to international format for WhatsApp.
    Assumes Pakistan numbers if no country code.
    """
    # Remove spaces, dashes, parentheses
    phone = "".join(filter(str.isdigit, phone))
    
    # Pakistan: 03xx → +923xx
    if phone.startswith("03") and len(phone) == 11:
        phone = "92" + phone[1:]
    
    # Add + if missing
    if not phone.startswith("+"):
        phone = "+" + phone
    
    return f"whatsapp:{phone}"


def build_booking_message(appointment: dict, clinic_name: str) -> str:
    """Build the WhatsApp notification message."""
    booking_for = appointment.get("doctor_name") or appointment.get("test_name", "N/A")
    booking_type = "Dr." if appointment["booking_type"] == "doctor" else "Test:"

    return (
        f"🏥 *{clinic_name}* — Appointment Confirmed!\n\n"
        f"👤 Patient: *{appointment['patient_name']}*\n"
        f"📅 Date: *{appointment['date']}*\n"
        f"⏰ Time: *{appointment['time_slot']}*\n"
        f"💊 {booking_type} *{booking_for}*\n"
        f"💰 Fee: *PKR {appointment['fee']:.0f}*\n"
        f"🆔 Booking ID: `{appointment['appointment_id'][:8].upper()}`\n\n"
        f"Please arrive 10 minutes early. Thank you for choosing {clinic_name}! 🙏"
    )


async def send_whatsapp_notification(appointment: dict, clinic_name: str) -> bool:
    """
    Send a WhatsApp message via Twilio.
    Returns True if sent successfully, False otherwise.
    """
    if not settings.twilio_account_sid or not settings.twilio_auth_token:
        logger.warning("Twilio credentials not configured — skipping WhatsApp notification")
        return False

    try:
        client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
        to_number = format_phone_for_whatsapp(appointment["phone"])
        message_body = build_booking_message(appointment, clinic_name)

        message = client.messages.create(
            body=message_body,
            from_=settings.twilio_whatsapp_from,
            to=to_number,
        )

        logger.info(f"✅ WhatsApp sent to {to_number}, SID={message.sid}")
        return True

    except TwilioRestException as e:
        logger.error(f"❌ Twilio error: {e.msg}")
        return False
    except Exception as e:
        logger.error(f"❌ WhatsApp notification failed: {str(e)}")
        return False
