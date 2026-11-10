"""Entry point for Redovisningsakademin."""

import streamlit as st

from ra.services import learner
from ra.ui.i18n import render_language_switch
from ra.ui.pages import designprov
from ra.ui.theme import apply_theme

APP_NAME = "Redovisningsakademin"

st.set_page_config(page_title=APP_NAME, layout="wide")
apply_theme()
learner.get_or_create()
render_language_switch()
designprov.render()
