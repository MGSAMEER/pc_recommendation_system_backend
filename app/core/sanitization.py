"""
Data sanitization utilities for PC Recommendation System
Provides comprehensive sanitization for user inputs and data processing
"""

import re
import html
import bleach
from typing import Any, Dict, List, Union, Optional
from urllib.parse import quote, unquote


class DataSanitizer:
    """Comprehensive data sanitization utilities"""

    # Dangerous patterns to remove
    DANGEROUS_PATTERNS = [
        r'<script[^>]*>.*?</script>',  # Script tags
        r'<iframe[^>]*>.*?</iframe>',  # Iframe tags
        r'<object[^>]*>.*?</object>',  # Object tags
        r'<embed[^>]*>.*?</embed>',   # Embed tags
        r'javascript:',               # JavaScript URLs
        r'vbscript:',                 # VBScript URLs
        r'data:',                     # Data URLs (potentially dangerous)
        r'on\w+\s*=',                 # Event handlers
        r'javascript\s*:',            # JavaScript pseudo-protocol
        r'expression\s*\(',           # CSS expressions
        r'vbscript\s*:',              # VBScript pseudo-protocol
    ]

    # Allowed HTML tags for rich text content
    ALLOWED_HTML_TAGS = [
        'p', 'br', 'strong', 'em', 'u', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'ul', 'ol', 'li', 'blockquote', 'code', 'pre', 'a', 'img'
    ]

    # Allowed HTML attributes
    ALLOWED_HTML_ATTRIBUTES = {
        'a': ['href', 'title', 'target'],
        'img': ['src', 'alt', 'title', 'width', 'height']
    }

    @classmethod
    def sanitize_text(cls, text: str, max_length: int = 10000) -> str:
        """Sanitize plain text input"""
        if not isinstance(text, str):
            return ""

        # Convert to string and strip whitespace
        sanitized = str(text).strip()

        # Limit length
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length]

        # Remove dangerous patterns
        for pattern in cls.DANGEROUS_PATTERNS:
            sanitized = re.sub(pattern, '', sanitized, flags=re.IGNORECASE | re.DOTALL)

        # HTML encode to prevent XSS
        sanitized = html.escape(sanitized, quote=True)

        return sanitized

    @classmethod
    def sanitize_html(cls, html_content: str, max_length: int = 50000) -> str:
        """Sanitize HTML content while preserving allowed tags"""
        if not isinstance(html_content, str):
            return ""

        # Limit length first
        if len(html_content) > max_length:
            html_content = html_content[:max_length]

        # Use bleach for comprehensive HTML sanitization
        sanitized = bleach.clean(
            html_content,
            tags=cls.ALLOWED_HTML_TAGS,
            attributes=cls.ALLOWED_HTML_ATTRIBUTES,
            strip=True
        )

        return sanitized

    @classmethod
    def sanitize_filename(cls, filename: str) -> str:
        """Sanitize filename to prevent directory traversal and other attacks"""
        if not isinstance(filename, str):
            return "unnamed_file"

        # Remove path separators
        sanitized = re.sub(r'[\/\\]', '', filename)

        # Remove dangerous characters
        sanitized = re.sub(r'[<>:"|?*]', '', sanitized)

        # Remove control characters
        sanitized = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', sanitized)

        # Limit length
        if len(sanitized) > 255:
            name, ext = sanitized.rsplit('.', 1) if '.' in sanitized else (sanitized, '')
            if ext:
                sanitized = name[:250] + '.' + ext
            else:
                sanitized = sanitized[:255]

        # Ensure not empty
        if not sanitized.strip():
            sanitized = "unnamed_file"

        return sanitized

    @classmethod
    def sanitize_url(cls, url: str) -> str:
        """Sanitize URL to prevent malicious redirects"""
        if not isinstance(url, str):
            return ""

        # URL decode first
        try:
            decoded_url = unquote(url)
        except:
            return ""

        # Remove dangerous protocols
        dangerous_protocols = ['javascript:', 'vbscript:', 'data:', 'file:']
        for protocol in dangerous_protocols:
            if decoded_url.lower().startswith(protocol):
                return ""

        # URL encode to prevent injection
        try:
            sanitized = quote(decoded_url, safe=':/?#[]@!$&\'()*+,;=-._~')
        except:
            return ""

        return sanitized

    @classmethod
    def sanitize_email(cls, email: str) -> str:
        """Sanitize email address"""
        if not isinstance(email, str):
            return ""

        # Basic email pattern validation and sanitization
        email = email.strip().lower()

        # Remove any HTML
        email = re.sub(r'<[^>]+>', '', email)

        # Remove dangerous characters
        email = re.sub(r'[<>]', '', email)

        # Basic email validation
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            return ""

        return email

    @classmethod
    def sanitize_numeric(cls, value: Any, min_val: float = None, max_val: float = None) -> Optional[float]:
        """Sanitize numeric input"""
        try:
            # Convert to float
            numeric_value = float(value)

            # Check bounds
            if min_val is not None and numeric_value < min_val:
                return None
            if max_val is not None and numeric_value > max_val:
                return None

            return numeric_value
        except (ValueError, TypeError):
            return None

    @classmethod
    def sanitize_list(cls, items: List[Any], item_sanitizer: callable = None, max_items: int = 100) -> List[Any]:
        """Sanitize list of items"""
        if not isinstance(items, list):
            return []

        # Limit list length
        sanitized_list = items[:max_items]

        # Apply item sanitizer if provided
        if item_sanitizer:
            sanitized_list = [item_sanitizer(item) for item in sanitized_list]
            # Filter out None values
            sanitized_list = [item for item in sanitized_list if item is not None]

        return sanitized_list

    @classmethod
    def sanitize_dict(cls, data: Dict[str, Any], field_sanitizers: Dict[str, callable] = None) -> Dict[str, Any]:
        """Sanitize dictionary data"""
        if not isinstance(data, dict):
            return {}

        sanitized = {}

        for key, value in data.items():
            # Sanitize key
            clean_key = cls.sanitize_text(str(key), 100)

            # Apply field-specific sanitizer if available
            if field_sanitizers and clean_key in field_sanitizers:
                clean_value = field_sanitizers[clean_key](value)
                if clean_value is not None:
                    sanitized[clean_key] = clean_value
            else:
                # Default sanitization based on value type
                if isinstance(value, str):
                    sanitized[clean_key] = cls.sanitize_text(value)
                elif isinstance(value, (int, float)):
                    numeric_value = cls.sanitize_numeric(value)
                    if numeric_value is not None:
                        sanitized[clean_key] = numeric_value
                elif isinstance(value, list):
                    sanitized[clean_key] = cls.sanitize_list(value)
                elif isinstance(value, dict):
                    sanitized[clean_key] = cls.sanitize_dict(value)
                else:
                    # Convert to string and sanitize
                    sanitized[clean_key] = cls.sanitize_text(str(value))

        return sanitized

    @classmethod
    def sanitize_search_query(cls, query: str) -> str:
        """Sanitize search query with special handling for search terms"""
        if not isinstance(query, str):
            return ""

        # Basic text sanitization
        sanitized = cls.sanitize_text(query, 500)

        # Allow some special characters for search
        # Remove only the most dangerous ones
        sanitized = re.sub(r'[<>]', '', sanitized)

        return sanitized.strip()

    @classmethod
    def sanitize_sql_like(cls, value: str) -> str:
        """Sanitize value for SQL LIKE queries"""
        if not isinstance(value, str):
            return ""

        # Escape SQL LIKE wildcards
        sanitized = value.replace('%', '\\%').replace('_', '\\_')

        # Apply text sanitization
        sanitized = cls.sanitize_text(sanitized, 500)

        return sanitized


class ContentFilter:
    """Content filtering utilities for inappropriate content"""

    # Profanity patterns (basic implementation - extend as needed)
    PROFANITY_PATTERNS = [
        r'\b(?:fuc?k|shit|damn|crap)\b',
        # Add more patterns as needed
    ]

    @classmethod
    def contains_profanity(cls, text: str) -> bool:
        """Check if text contains profanity"""
        if not isinstance(text, str):
            return False

        text_lower = text.lower()
        for pattern in cls.PROFANITY_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return True
        return False

    @classmethod
    def filter_profanity(cls, text: str, replacement: str = "***") -> str:
        """Filter profanity from text"""
        if not isinstance(text, str):
            return text

        filtered = text
        for pattern in cls.PROFANITY_PATTERNS:
            filtered = re.sub(pattern, replacement, filtered, flags=re.IGNORECASE)

        return filtered

    @classmethod
    def is_safe_content(cls, content: str) -> bool:
        """Check if content is safe for display"""
        if not isinstance(content, str):
            return True

        # Check for profanity
        if cls.contains_profanity(content):
            return False

        # Check for excessive caps
        if len(content) > 10 and sum(1 for c in content if c.isupper()) / len(content) > 0.8:
            return False

        return True


# Global instances
data_sanitizer = DataSanitizer()
content_filter = ContentFilter()

