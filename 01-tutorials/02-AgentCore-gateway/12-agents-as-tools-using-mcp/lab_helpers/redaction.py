"""
Utility functions for redacting sensitive information in logs
"""


def redact_secret(value: str, visible_chars: int = 4) -> str:
    """
    Redact a secret value, showing only the last few characters
    
    Args:
        value: The secret value to redact
        visible_chars: Number of characters to show at the end
        
    Returns:
        Redacted string like "****abc123"
    """
    if not value or len(value) <= visible_chars:
        return "****"
    return f"****{value[-visible_chars:]}"


def redact_email(email: str) -> str:
    """
    Redact an email address, showing only domain
    
    Args:
        email: Email address to redact
        
    Returns:
        Redacted email like "****@example.com"
    """
    if not email or '@' not in email:
        return "****"
    parts = email.split('@')
    return f"****@{parts[1]}"
