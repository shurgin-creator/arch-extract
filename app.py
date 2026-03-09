import streamlit as st
import traceback
try:
    import core_app
    if hasattr(core_app, 'main'):
        core_app.main()
except Exception as e:
    st.error("🚨 Critical Startup Error Detected")
    st.code(traceback.format_exc(), language="python")
    st.stop()
