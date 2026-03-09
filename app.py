import streamlit as st
import traceback
try:
# This runs the actual app safely
import core_app
except Exception as e:
st.error("🚨 Critical Startup Error Detected")
st.code(traceback.format_exc(), language="python")
st.stop()
