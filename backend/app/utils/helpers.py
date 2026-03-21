"""
Helper Utilities
ParcelFlow - Multi-tenant Logistics Platform
"""
import random
import string
from datetime import datetime
from decimal import Decimal
from typing import Optional


def generate_unique_id(prefix: str = "", length: int = 8) -> str:
    """
    Generate a unique identifier with optional prefix.
    Format: PREFIX-YYYYMMDD-XXXXXXXX
    """
    timestamp = datetime.now().strftime("%Y%m%d")
    random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))
    
    if prefix:
        return f"{prefix}-{timestamp}-{random_part}"
    return f"{timestamp}-{random_part}"


def format_currency(
    amount: Decimal,
    currency: str = "NGN",
    include_symbol: bool = True
) -> str:
    """
    Format a decimal amount as currency string.
    """
    # Format with 2 decimal places and thousand separators
    formatted = f"{amount:,.2f}"
    
    if include_symbol:
        symbols = {
            "NGN": "₦",
            "USD": "$",
            "GBP": "£",
            "EUR": "€"
        }
        symbol = symbols.get(currency, currency + " ")
        return f"{symbol}{formatted}"
    
    return formatted


def format_date(
    date_string: Optional[str],
    format_type: str = "datetime"
) -> Optional[str]:
    """
    Format a date string to human-readable format.
    
    format_type options:
    - datetime: "Jan 15, 2024, 10:30 AM"
    - date: "Jan 15, 2024"
    - time: "10:30 AM"
    - full: "January 15, 2024, 10:30 AM"
    """
    if not date_string:
        return None
    
    try:
        # Parse the date string
        if "T" in date_string:
            dt = datetime.fromisoformat(date_string.replace("Z", "+00:00"))
        else:
            dt = datetime.fromisoformat(date_string)
        
        formats = {
            "datetime": "%b %d, %Y, %I:%M %p",
            "date": "%b %d, %Y",
            "time": "%I:%M %p",
            "full": "%B %d, %Y, %I:%M %p",
            "iso": "%Y-%m-%dT%H:%M:%S"
        }
        
        return dt.strftime(formats.get(format_type, formats["datetime"]))
    except (ValueError, TypeError):
        return date_string


def slugify(text: str) -> str:
    """
    Convert text to URL-friendly slug.
    """
    import re
    # Convert to lowercase
    text = text.lower()
    # Replace spaces with hyphens
    text = re.sub(r'\s+', '-', text)
    # Remove non-alphanumeric characters except hyphens
    text = re.sub(r'[^a-z0-9-]', '', text)
    # Remove multiple hyphens
    text = re.sub(r'-+', '-', text)
    # Remove leading/trailing hyphens
    text = text.strip('-')
    return text


def calculate_pagination(
    total: int,
    page: int,
    page_size: int
) -> dict:
    """
    Calculate pagination metadata.
    """
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "has_next": page < total_pages,
        "has_prev": page > 1
    }


def mask_phone(phone: str) -> str:
    """
    Mask phone number for privacy.
    Example: +2348012345678 -> +23480***45678
    """
    if not phone or len(phone) < 8:
        return phone
    
    # Keep first 5 and last 4 characters visible
    return f"{phone[:5]}***{phone[-4:]}"


def mask_email(email: str) -> str:
    """
    Mask email address for privacy.
    Example: john.doe@example.com -> j***@example.com
    """
    if not email or "@" not in email:
        return email
    
    local, domain = email.split("@", 1)
    if len(local) <= 1:
        return f"{local}@{domain}"
    
    return f"{local[0]}***@{domain}"


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate text to specified length with suffix.
    """
    if not text or len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)].rsplit(" ", 1)[0] + suffix


def validate_phone(phone: str, country_code: str = "+234") -> str:
    """
    Validate and normalize phone number.
    """
    if not phone:
        return phone
    
    # Remove spaces and dashes
    phone = phone.replace(" ", "").replace("-", "")
    
    # Add country code if missing
    if phone.startswith("0"):
        phone = country_code + phone[1:]
    elif not phone.startswith("+"):
        phone = country_code + phone
    
    return phone
