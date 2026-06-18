"""Threat Intelligence-specific exceptions."""


class ThreatIntelligenceError(Exception):
    """Base exception for all threat intelligence-related errors."""


class ThreatIntelligenceClientError(ThreatIntelligenceError):
    """Client-related errors when communicating with VirusTotal API."""
