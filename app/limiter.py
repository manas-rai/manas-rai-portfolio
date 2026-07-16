from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address

# In-memory, per-process limiter. State resets on redeploy/cold start — an
# accepted v1 limitation (design doc §4.3); the honeypot is the durable defense.
limiter = Limiter(key_func=get_remote_address)
