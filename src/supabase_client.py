"""
Supabase client singleton for Streamlit sessions.
Handles auth token persistence across Streamlit reruns via session state.
"""

import os
import streamlit as st
from supabase import create_client, Client


def get_supabase() -> Client:
    """
    Get or create the Supabase client for the current session.
    Restores the auth session from stored tokens so the JWT is included
    in every subsequent request (required for RLS enforcement).

    Raises:
        ValueError: if SUPABASE_URL or SUPABASE_KEY are not configured.
    """
    url = st.secrets.get("SUPABASE_URL") or os.getenv("SUPABASE_URL")
    key = st.secrets.get("SUPABASE_KEY") or os.getenv("SUPABASE_KEY")

    if not url or not key:
        raise ValueError(
            "SUPABASE_URL and SUPABASE_KEY must be set in Streamlit secrets or environment variables."
        )

    if "supabase_client" not in st.session_state:
        client = create_client(url, key)

        # Restore a previous session if tokens are still stored
        access_token = st.session_state.get("supabase_access_token")
        refresh_token = st.session_state.get("supabase_refresh_token")
        if access_token and refresh_token:
            try:
                client.auth.set_session(access_token, refresh_token)
            except Exception:
                # Tokens expired or invalid — force re-login
                st.session_state.pop("supabase_access_token", None)
                st.session_state.pop("supabase_refresh_token", None)
                st.session_state.pop("user", None)

        st.session_state.supabase_client = client

    return st.session_state.supabase_client
