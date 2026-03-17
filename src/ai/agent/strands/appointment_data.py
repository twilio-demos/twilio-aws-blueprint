"""Mock appointment data for Owl Health scheduling."""

from datetime import datetime, timedelta
from typing import Dict, List, Optional


# Define appointment types
APPOINTMENT_TYPES = {
    "general": "General checkup or routine visit",
    "specialist": "Specialist consultation",
    "follow-up": "Follow-up appointment",
}


def get_available_appointments(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    appointment_type: Optional[str] = None,
) -> Dict[str, List[Dict[str, str]]]:
    """
    Get available appointment slots (mock data).

    Args:
        start_date: Start date in YYYY-MM-DD format (default: today)
        end_date: End date in YYYY-MM-DD format (default: 7 days from start)
        appointment_type: Filter by appointment type (general, specialist, follow-up)

    Returns:
        Dict mapping dates to lists of appointment slots
    """
    # Parse dates or use defaults
    if start_date:
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d")
        except ValueError:
            start = datetime.now()
    else:
        start = datetime.now()

    if end_date:
        try:
            end = datetime.strptime(end_date, "%Y-%m-%d")
        except ValueError:
            end = start + timedelta(days=7)
    else:
        end = start + timedelta(days=7)

    # Generate appointment slots
    appointments = {}
    current_date = start

    # Define daily slots
    daily_slots = [
        {"time": "09:00", "type": "general", "doctor": "Dr. Smith", "duration": "30 min"},
        {
            "time": "10:30",
            "type": "general",
            "doctor": "Dr. Johnson",
            "duration": "30 min",
        },
        {
            "time": "13:00",
            "type": "specialist",
            "doctor": "Dr. Chen",
            "duration": "45 min",
        },
        {
            "time": "14:30",
            "type": "follow-up",
            "doctor": "Dr. Smith",
            "duration": "20 min",
        },
        {
            "time": "16:00",
            "type": "general",
            "doctor": "Dr. Johnson",
            "duration": "30 min",
        },
    ]

    while current_date <= end:
        # Skip weekends (Saturday=5, Sunday=6)
        if current_date.weekday() < 5:
            date_str = current_date.strftime("%Y-%m-%d")

            # Filter by appointment type if specified
            if appointment_type:
                filtered_slots = [
                    slot for slot in daily_slots if slot["type"] == appointment_type
                ]
            else:
                filtered_slots = daily_slots.copy()

            if filtered_slots:
                appointments[date_str] = filtered_slots

        current_date += timedelta(days=1)

    return appointments
