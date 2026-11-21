"""Admin authentication helpers for the spatial-eval Streamlit app.

These functions interact with Streamlit's secrets and session state
to manage read-only vs admin modes.
"""
from __future__ import annotations

import os

import streamlit as st


def admin_configured_token() -> str:
    """Resolve admin token from environment variable or Streamlit secrets.

    Checks SPATIAL_EVAL_ADMIN_TOKEN env var first, then st.secrets. Returns
    an empty string if neither is configured.
    """
    env_token = os.environ.get("SPATIAL_EVAL_ADMIN_TOKEN", "").strip()
    if env_token:
        return env_token
    try:
        secret_token = str(st.secrets.get("SPATIAL_EVAL_ADMIN_TOKEN", "")).strip()
    except Exception:
        secret_token = ""
    return secret_token


def admin_bypass_enabled() -> bool:
    """Local development bypass for admin-only controls.

    Set SPATIAL_EVAL_ADMIN_BYPASS=1 (or 'true' or 'yes') to skip token auth
    when running locally. Never used in production / Community Cloud.
    """
    return os.environ.get("SPATIAL_EVAL_ADMIN_BYPASS", "").lower() in {"1", "true", "yes"}


def is_admin_authenticated() -> tuple[bool, str]:
    """Return (is_authenticated, message) for the current Streamlit session.

    Authentication flow:
      0. Cloud environment → permanently locked (protection against API abuse)
      1. SPATIAL_EVAL_ADMIN_BYPASS env var → bypass (local dev only)
      2. No token configured → permanently locked
      3. Session state token matches configured token → authenticated
      4. Otherwise → read-only mode
    """
    is_cloud = (
        os.environ.get("STREAMLIT_SERVER_HEADLESS", "false").lower() == "true"
        or os.environ.get("VERCEL", "0") in {"1", "true", "yes"}
        or os.environ.get("RENDER", "false").lower() == "true"
    )
    if is_cloud:
        return False, "Admin controls are permanently disabled in cloud environments."

    if admin_bypass_enabled():
        return True, "Admin bypass enabled via SPATIAL_EVAL_ADMIN_BYPASS."

    configured_token = admin_configured_token()
    if not configured_token:
        return False, "Admin token is not configured; run controls are disabled."

    entered_token = str(st.session_state.get("prompt_experiment_admin_token", "")).strip()
    if not entered_token:
        return False, "Read-only mode: enter a valid admin token to unlock run controls."
        
    if entered_token == configured_token:
        return True, "Admin token verified."

    return False, "Invalid admin token provided. Still in read-only mode."
