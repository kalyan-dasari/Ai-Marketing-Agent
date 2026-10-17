import socket
import ipaddress
import re
from urllib.parse import urlparse

ALLOWED_EXTENSIONS = {'.md', '.markdown', '.txt', '.rst'}
MAX_UPLOAD_SIZE = 2 * 1024 * 1024  # 2MB
MAX_REMOTE_FETCH_SIZE = 1 * 1024 * 1024  # 1MB
REQUEST_TIMEOUT = 5  # seconds

def is_safe_url(url: str) -> tuple[bool, str]:
    """
    Validates a URL against Server-Side Request Forgery (SSRF).
    Ensures URL uses http/https, has a valid hostname, and resolves only to public, non-reserved IP addresses.
    """
    if not url or not isinstance(url, str):
        return False, "URL is required and must be a string."
    
    url = url.strip()
    try:
        parsed = urlparse(url)
    except Exception:
        return False, "Invalid URL format."
        
    if parsed.scheme.lower() not in ('http', 'https'):
        return False, "Only HTTP and HTTPS URLs are allowed."
        
    hostname = parsed.hostname
    if not hostname:
        return False, "URL must have a valid hostname."
        
    # Block localhost and common local names
    hostname_lower = hostname.lower()
    if hostname_lower in ('localhost', '127.0.0.1', '::1', '0.0.0.0', 'local', 'internal'):
        return False, "Localhost and loopback addresses are prohibited."

    # Validate resolved IP addresses
    try:
        addr_info = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        return False, f"Could not resolve host '{hostname}'."
    except Exception as e:
        return False, f"Network error resolving host: {str(e)}"

    for addr in addr_info:
        ip_str = addr[4][0]
        try:
            ip = ipaddress.ip_address(ip_str)
            if ip.is_private or ip.is_loopback or ip.is_reserved or ip.is_link_local or ip.is_multicast:
                return False, f"Prohibited address: {ip_str} is in a private or reserved network."
        except ValueError:
            return False, f"Invalid IP address resolved: {ip_str}"

    return True, ""

def is_allowed_file(filename: str) -> bool:
    """Checks if uploaded file extension is an allowed document type."""
    if not filename or '.' not in filename:
        return False
    ext = '.' + filename.rsplit('.', 1)[1].lower()
    return ext in ALLOWED_EXTENSIONS

def sanitize_text(text: str, max_chars: int = 15000) -> str:
    """
    Normalizes whitespace and removes null bytes or control characters
    while preserving newlines and markdown characters.
    """
    if not text:
        return ""
    # Strip null bytes and non-printable control characters (except newline, cr, tab)
    cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    return cleaned[:max_chars].strip()
