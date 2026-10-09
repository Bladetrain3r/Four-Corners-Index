"""The feedback form's settings (data/manual/feedback.json), checked before they reach the site: the form is off unless they are complete."""
from __future__ import annotations

import ipaddress
from typing import Any
from urllib.parse import urlsplit

from pipeline import site_data


def config() -> dict[str, Any] | None:
    """None while the form is off; otherwise the settings the page needs. Raises ValueError for a half-set or unsafe configuration."""
    raw = site_data.manual("feedback.json")
    endpoint, contact = raw.get("endpoint"), raw.get("contact")
    if endpoint is None and contact is None:
        return None
    if not endpoint or not contact:
        raise ValueError("feedback.json: set both 'endpoint' and 'contact', or neither (a form that collects an email must say who to ask to delete it)")
    u = urlsplit(endpoint)
    if u.scheme != "https" or not u.hostname or u.username or u.password or u.fragment or u.query or u.path != "/feedback":
        raise ValueError(f"feedback.json: endpoint must be a plain https URL ending in /feedback, got {endpoint!r}")
    try:
        ipaddress.ip_address(u.hostname)
    except ValueError:
        pass
    else:
        raise ValueError("feedback.json: endpoint must be a host name, not an IP address (it needs a certificate)")
    days = raw.get("retention_days")
    if isinstance(days, bool) or not isinstance(days, int) or not 1 <= days <= 365:
        raise ValueError("feedback.json: retention_days must be a whole number of days from 1 to 365")
    if not isinstance(contact, str) or len(contact) > 200:
        raise ValueError("feedback.json: contact must be a short string")
    return {"endpoint": endpoint, "host": u.hostname, "contact": contact, "retention_days": days, "max_comment": 1000}
