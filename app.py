"""Entry point for Redovisningsakademin: page config, sparkod, navigation."""

import streamlit as st

from ra.services import learner
from ra.ui.i18n import render_language_switch
from ra.ui.navigation import build_navigation
from ra.ui.theme import apply_theme

APP_NAME = "Redovisningsakademin"

st.set_page_config(page_title=APP_NAME, layout="wide")
apply_theme()
learner.get_or_create()
page = build_navigation()
render_language_switch()
page.run()
