"""CVE-specific exceptions."""


class CVEError(Exception):
    """Base exception for all CVE-related errors."""


class CVEClientError(CVEError):
    """Client-related errors when communicating with CVE API."""
