"""Strands-compatible tools for conversation agent."""

import json
from datetime import datetime
from typing import Optional

from strands import tool

from src.ai.agent.strands.appointment_data import (
    APPOINTMENT_TYPES,
    get_available_appointments,
)


@tool
def update_language_tool(language_code: str) -> str:
    """
    Update the conversation language.

    Args:
        language_code: Full locale code with region (e.g., 'en-US', 'es-US', 'es-MX', 'fr-FR', 'pt-BR')

    Returns:
        Language code to be handled by runner
    """
    # Map simple codes to full locales if needed
    language_map = {
        "en": "en-US",
        "es": "es-US",
        "fr": "fr-FR",
        "pt": "pt-BR",
        "de": "de-DE",
        "it": "it-IT",
        "ja": "ja-JP",
        "ko": "ko-KR",
        "zh": "zh-CN",
    }

    # If it's a simple code, map it to full locale
    # If it's already a full locale (contains '-'), use as-is
    if "-" not in language_code:
        language_code = language_map.get(language_code.lower(), f"{language_code}-US")

    return language_code


@tool
def perform_handoff_tool(queue_name: str, reason: str) -> str:
    """
    Perform handoff to human agent.

    Args:
        queue_name: Target queue for handoff
        reason: Reason for handoff

    Returns:
        JSON string with handoff details
    """
    return json.dumps({"queue_name": queue_name, "reason": reason})


@tool
def update_hints_tool(hints: str) -> str:
    """
    Update conversation hints.

    Args:
        hints: New hints to apply

    Returns:
        JSON string with hints
    """
    return json.dumps({"hints": hints})


@tool
def complete_or_escalate_tool(action: str, summary: Optional[str] = None) -> str:
    """
    Complete the conversation or escalate.

    Args:
        action: 'complete' or 'escalate'
        summary: Optional summary of the conversation

    Returns:
        JSON string with action details
    """
    return json.dumps({"action": action, "summary": summary})


@tool
def look_up_availability(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    appointment_type: Optional[str] = None,
) -> str:
    """
    Look up available appointment slots.

    Args:
        start_date: Start date in YYYY-MM-DD format (default: today)
        end_date: End date in YYYY-MM-DD format (default: 7 days from start)
        appointment_type: Filter by type: 'general', 'specialist', or 'follow-up'

    Returns:
        JSON string with available appointments and appointment types
    """
    # Get available appointments
    appointments = get_available_appointments(start_date, end_date, appointment_type)

    return json.dumps(
        {
            "success": True,
            "appointments": appointments,
            "appointment_types": APPOINTMENT_TYPES,
        }
    )


@tool
def schedule_appointment(
    date: str,
    time: str,
    appointment_type: str,
    doctor: str,
    patient_name: str,
    patient_phone: Optional[str] = None,
    reason: Optional[str] = None,
) -> str:
    """
    Schedule an appointment for a patient.

    Args:
        date: Appointment date in YYYY-MM-DD format
        time: Appointment time in HH:MM format (e.g., "09:00")
        appointment_type: Type of appointment: 'general', 'specialist', or 'follow-up'
        doctor: Doctor's name
        patient_name: Patient's full name
        patient_phone: Patient's phone number (optional)
        reason: Reason for appointment (optional)

    Returns:
        JSON string with confirmation details or error
    """
    # Validate required fields
    if not all([date, time, appointment_type, doctor, patient_name]):
        return json.dumps(
            {
                "success": False,
                "error": "Missing required fields: date, time, appointment_type, doctor, patient_name",
            }
        )

    # Validate appointment type
    if appointment_type not in APPOINTMENT_TYPES:
        return json.dumps(
            {
                "success": False,
                "error": f"Invalid appointment type. Must be one of: {', '.join(APPOINTMENT_TYPES.keys())}",
            }
        )

    # Generate confirmation number: OWL + YYYYMMDD + HHMM
    try:
        date_obj = datetime.strptime(date, "%Y-%m-%d")
        time_obj = datetime.strptime(time, "%H:%M")
        confirmation_number = f"OWL{date_obj.strftime('%Y%m%d')}{time_obj.strftime('%H%M')}"
    except ValueError:
        return json.dumps(
            {
                "success": False,
                "error": "Invalid date or time format. Use YYYY-MM-DD for date and HH:MM for time",
            }
        )

    # Build appointment details
    appointment_details = {
        "success": True,
        "confirmation_number": confirmation_number,
        "date": date,
        "time": time,
        "appointment_type": appointment_type,
        "doctor": doctor,
        "patient_name": patient_name,
    }

    if patient_phone:
        appointment_details["patient_phone"] = patient_phone

    if reason:
        appointment_details["reason"] = reason

    return json.dumps(appointment_details)
