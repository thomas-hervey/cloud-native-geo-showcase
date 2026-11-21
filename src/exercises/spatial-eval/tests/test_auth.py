"""Tests for the auth UI helpers."""
from __future__ import annotations

import pytest

from ui.auth import (
    admin_configured_token,
    admin_bypass_enabled,
    is_admin_authenticated,
)


def test_admin_configured_token_from_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("SPATIAL_EVAL_ADMIN_TOKEN", "supersecret")
    assert admin_configured_token() == "supersecret"

    monkeypatch.delenv("SPATIAL_EVAL_ADMIN_TOKEN", raising=False)
    assert admin_configured_token() == ""


def test_admin_bypass_enabled(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("SPATIAL_EVAL_ADMIN_BYPASS", "true")
    assert admin_bypass_enabled() is True

    monkeypatch.setenv("SPATIAL_EVAL_ADMIN_BYPASS", "1")
    assert admin_bypass_enabled() is True

    monkeypatch.setenv("SPATIAL_EVAL_ADMIN_BYPASS", "false")
    assert admin_bypass_enabled() is False

    monkeypatch.delenv("SPATIAL_EVAL_ADMIN_BYPASS", raising=False)
    assert admin_bypass_enabled() is False


def test_is_admin_authenticated_bypass(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("SPATIAL_EVAL_ADMIN_BYPASS", "true")
    is_auth, msg = is_admin_authenticated()
    assert is_auth is True
    assert "bypass enabled" in msg.lower()


def test_is_admin_authenticated_no_token_configured(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("SPATIAL_EVAL_ADMIN_TOKEN", raising=False)
    monkeypatch.setenv("SPATIAL_EVAL_ADMIN_BYPASS", "false")
    
    is_auth, msg = is_admin_authenticated()
    assert is_auth is False
    assert "not configured" in msg.lower()


def test_is_admin_authenticated_streamlit_context_mocked(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("SPATIAL_EVAL_ADMIN_TOKEN", "supersecret")
    monkeypatch.setenv("SPATIAL_EVAL_ADMIN_BYPASS", "false")
    
    # Normally Streamlit handles session_state, but we mock the check inside streamlit context
    # by pretending there is no user token in session state
    is_auth, msg = is_admin_authenticated()
    assert is_auth is False
    assert "enter a valid admin token" in msg.lower()


def test_is_admin_authenticated_invalid_token(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("SPATIAL_EVAL_ADMIN_TOKEN", "supersecret")
    monkeypatch.setenv("SPATIAL_EVAL_ADMIN_BYPASS", "false")
    
    import streamlit as st
    monkeypatch.setattr(st, "session_state", {"prompt_experiment_admin_token": "wrongtoken"})
    
    is_auth, msg = is_admin_authenticated()
    assert is_auth is False
    assert "invalid admin token" in msg.lower()
