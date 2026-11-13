"""Feedback panel: the five parts in fixed order.

1 Vad som blev fel, 2 Varför, 3 Rätt hantering, 4 Regel med källa, 5 Tips.
A right answer shows a short confirmation, any note on accepted
alternative accounts, the rule and the tip. All text is escaped.
"""

from html import escape

import streamlit as st

from ra.services.views import FeedbackView
from ra.ui.components.voucher import voucher_table_html
from ra.ui.i18n import t


def _part(label: str, body_html: str) -> str:
    return (f'<div class="ra-feedback-part"><div class="ra-feedback-label">{escape(label)}</div>'
            f"{body_html}</div>")


def _paragraph(text: str) -> str:
    return f"<p>{escape(text)}</p>"


def _treatment(view: FeedbackView) -> str:
    voucher = voucher_table_html(view.treatment_voucher) if view.treatment_voucher else ""
    notes = "".join(_paragraph(note) for note in view.notes)
    return _paragraph(view.treatment) + voucher + notes


def _rule(view: FeedbackView) -> str:
    link = (f'<a href="{escape(view.rule_url, quote=True)}" target="_blank" '
            f'rel="noopener noreferrer">{escape(t("Läs regeln hos källan"))}</a>')
    return _paragraph(f"{view.rule_reference}: {view.rule_title}.") + f"<p>{link}</p>"


def feedback_panel(view: FeedbackView) -> None:
    if view.correct:
        parts = [_paragraph(note) for note in view.notes]
        parts += [_part(t("Regel"), _rule(view)), _part(t("Tips"), _paragraph(view.tip))]
        heading = f"✓ {view.heading}"
        css = "correct"
    else:
        parts = [
            _part(t("Vad som blev fel"), _paragraph(view.what)),
            _part(t("Varför"), _paragraph(view.why)),
            _part(t("Rätt hantering"), _treatment(view)),
            _part(t("Regel"), _rule(view)),
            _part(t("Tips"), _paragraph(view.tip)),
        ]
        heading = f"✗ {view.heading}"
        css = "wrong"
    st.html(f'<div class="ra-feedback {css}"><div class="ra-feedback-heading">'
            f'{escape(heading)}</div>{"".join(parts)}</div>')
