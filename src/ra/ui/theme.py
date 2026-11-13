"""Design system: colours, global CSS and the basic display components.

Adapted and trimmed from the owner's ekonomistyrning app (MIT). Call
apply_theme() right after st.set_page_config(). Every component escapes
its text before building HTML, so no text is ever rendered as markup.
CSS classes use the "ra-" prefix. GLOBAL_CSS uses % interpolation against
COLORS, so a literal percent sign in CSS is written %%.
"""

from html import escape

import streamlit as st

COLORS: dict[str, str] = {
    "primary": "#1E40AF",
    "primary_light": "#3B82F6",
    "sidebar_bg": "#1E3A8A",
    "success": "#059669",
    "danger": "#DC2626",
    "warning": "#D97706",
    "bg": "#F3F4F6",
    "card_bg": "#FFFFFF",
    "text_primary": "#111827",
    "text_secondary": "#6B7280",
    "border": "#E5E7EB",
}

KPI_VARIANTS = ("default", "success", "danger", "warning")

_FONT_RANGE = (
    "U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, "
    "U+0304, U+0308, U+0329, U+2000-206F, U+20AC, U+2122, U+2191, U+2193, "
    "U+2212, U+2215, U+FEFF, U+FFFD"
)
_FONTS = (("Inter", 300), ("Inter", 400), ("Inter", 600), ("Inter", 700),
          ("IBM Plex Mono", 400), ("IBM Plex Mono", 500))


def _font_face(family: str, weight: int) -> str:
    file_name = f"{family.replace(' ', '')}-{weight}.woff2"
    return (
        f"@font-face {{ font-family: '{family}'; font-style: normal; "
        f"font-weight: {weight}; font-display: swap; "
        f"src: url(/app/static/fonts/{file_name}) format('woff2'); "
        f"unicode-range: {_FONT_RANGE}; }}"
    )


# Self-hosted fonts in static/fonts, served by Streamlit static serving:
# no third-party font request, so no visitor address leaves the app.
FONT_CSS: str = "\n".join(_font_face(family, weight) for family, weight in _FONTS)

GLOBAL_CSS: str = (
    """
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
div[data-testid="stDecoration"] {display: none;}

.main .block-container { padding: 32px 40px; max-width: 1200px; }
@media (max-width: 767.98px) {
    .main .block-container { padding: 20px 16px; }
}

/* --- Sidebar --- */
section[data-testid="stSidebar"] { background-color: %(sidebar_bg)s; }
section[data-testid="stSidebar"],
section[data-testid="stSidebar"] * { color: rgba(255,255,255,0.85); }
section[data-testid="stSidebar"] [data-testid="stWidgetLabel"] {
    color: rgba(255,255,255,0.6);
    font-size: 10.5px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

section[data-testid="stSidebar"] [data-testid^="stBaseLinkButton"] {
    background: transparent;
    border-color: rgba(255,255,255,0.4);
}

/* --- Page title --- */
.ra-page-title { margin-bottom: 24px; }
.ra-eyebrow {
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    color: %(primary_light)s;
    margin-bottom: 4px;
}
.ra-page-title h1 {
    font-size: 26px;
    font-weight: 700;
    color: %(text_primary)s;
    margin: 0 0 4px 0;
    padding: 0;
}
.ra-subtitle { font-size: 14px; color: %(text_secondary)s; }

/* --- Card --- */
.ra-card {
    background: %(card_bg)s;
    border: 1px solid %(border)s;
    border-radius: 4px;
    padding: 22px 24px;
    margin-bottom: 24px;
}
.ra-card h3 {
    font-size: 15px;
    font-weight: 700;
    color: %(text_primary)s;
    margin: 0 0 12px 0;
    padding: 0 0 12px 0;
    border-bottom: 1px solid %(border)s;
}
.ra-card p {
    font-size: 14px;
    line-height: 1.6;
    color: %(text_primary)s;
    margin: 0;
}

/* --- KPI tile --- */
.ra-kpi {
    background: %(card_bg)s;
    border: 1px solid %(border)s;
    border-left: 3px solid %(primary)s;
    border-radius: 4px;
    padding: 18px 20px;
    margin-bottom: 24px;
}
.ra-kpi.variant-success { border-left-color: %(success)s; }
.ra-kpi.variant-danger  { border-left-color: %(danger)s; }
.ra-kpi.variant-warning { border-left-color: %(warning)s; }
.ra-kpi-label {
    font-size: 10.5px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: %(text_secondary)s;
    margin-bottom: 6px;
}
.ra-kpi-value {
    font-size: clamp(19px, 2.1vw, 30px);
    font-weight: 700;
    color: %(text_primary)s;
    line-height: 1.15;
    overflow-wrap: anywhere;
}

/* --- Amounts: tabular figures, right aligned --- */
.ra-amount {
    font-family: "IBM Plex Mono", monospace;
    font-variant-numeric: tabular-nums;
    text-align: right;
}
.ra-kpi-value.ra-amount { text-align: left; }

/* --- Info box --- */
.ra-info {
    font-size: 14px;
    line-height: 1.6;
    color: %(text_secondary)s;
    background: %(bg)s;
    border-left: 3px solid %(primary_light)s;
    border-radius: 0 4px 4px 0;
    padding: 14px 20px;
    margin-bottom: 24px;
}
.ra-info strong { color: %(text_primary)s; }

/* --- Document (underlag) --- */
.ra-doc {
    background: %(card_bg)s;
    border: 1px solid %(border)s;
    border-radius: 4px;
    padding: 20px 24px;
    margin-bottom: 16px;
}
.ra-doc-head { display: flex; justify-content: space-between; gap: 16px; flex-wrap: wrap; }
.ra-doc-kind {
    font-size: 10.5px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: %(text_secondary)s;
}
.ra-doc-title { font-size: 18px; font-weight: 700; color: %(text_primary)s; }
.ra-doc-meta { font-size: 13px; color: %(text_secondary)s; text-align: right; }
.ra-doc-text { font-size: 13px; color: %(text_secondary)s; margin: 12px 0 0 0; }

/* --- Tables: verifikation, document rows, kontoutdrag --- */
.ra-table { width: 100%%; border-collapse: collapse; margin-top: 12px; font-size: 14px; }
.ra-table th {
    text-align: left;
    font-size: 10.5px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: %(text_secondary)s;
    border-bottom: 1px solid %(border)s;
    padding: 6px 8px;
}
.ra-table td { padding: 6px 8px; border-bottom: 1px solid %(border)s; color: %(text_primary)s; }
.ra-table th.ra-amount, .ra-table td.ra-amount { text-align: right; white-space: nowrap; }
.ra-table tr.ra-total td { font-weight: 600; border-bottom: none; }
.ra-hidden-amount { color: %(warning)s; font-weight: 600; }

/* --- Balance indicator: colour always with text and a sign --- */
.ra-balance {
    font-size: 13px;
    font-weight: 600;
    padding: 8px 12px;
    border-radius: 4px;
    margin: 8px 0 16px 0;
    border-left: 3px solid;
}
.ra-balance { color: %(text_secondary)s; border-color: %(border)s; background: %(bg)s; }
.ra-balance.ok { color: %(success)s; border-color: %(success)s; background: #ECFDF5; }
.ra-balance.off { color: %(danger)s; border-color: %(danger)s; background: #FEF2F2; }

/* --- Feedback panel: five parts in fixed order --- */
.ra-feedback {
    background: %(card_bg)s;
    border: 1px solid %(border)s;
    border-left: 3px solid %(danger)s;
    border-radius: 4px;
    padding: 18px 22px;
    margin: 16px 0 24px 0;
}
.ra-feedback.correct { border-left-color: %(success)s; }
.ra-feedback-heading { font-size: 16px; font-weight: 700; margin-bottom: 8px; }
.ra-feedback.correct .ra-feedback-heading { color: %(success)s; }
.ra-feedback.wrong .ra-feedback-heading { color: %(danger)s; }
.ra-feedback-part { margin-top: 14px; }
.ra-feedback-label {
    font-size: 10.5px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: %(text_secondary)s;
    margin-bottom: 4px;
}
.ra-feedback p { font-size: 14px; line-height: 1.6; color: %(text_primary)s; margin: 0; }
.ra-feedback a { color: %(primary)s; }
"""
    % COLORS
)


def apply_theme() -> None:
    """Inject fonts and global CSS. Call right after st.set_page_config()."""
    st.html(f"<style>{FONT_CSS}{GLOBAL_CSS}</style>")


def page_title(eyebrow: str, title: str, subtitle: str = "") -> None:
    """Page header: small eyebrow label, title and optional subtitle."""
    sub_html = f'<div class="ra-subtitle">{escape(subtitle)}</div>' if subtitle else ""
    st.html(
        f'<div class="ra-page-title">'
        f'<div class="ra-eyebrow">{escape(eyebrow)}</div>'
        f"<h1>{escape(title)}</h1>{sub_html}</div>"
    )


def card(title: str, body: str) -> None:
    """White card with a heading and one paragraph of text."""
    st.html(f'<div class="ra-card"><h3>{escape(title)}</h3><p>{escape(body)}</p></div>')


def kpi_tile(label: str, value: str, variant: str = "default", amount: bool = False) -> None:
    """Key figure tile with a coloured left border.

    The label always carries the meaning, so colour is never the only signal.
    Set ``amount`` for money so the value uses the tabular font.
    """
    if variant not in KPI_VARIANTS:
        raise ValueError(f"Unknown KPI variant: {variant}")
    variant_class = f" variant-{variant}" if variant != "default" else ""
    value_class = "ra-kpi-value ra-amount" if amount else "ra-kpi-value"
    st.html(
        f'<div class="ra-kpi{variant_class}">'
        f'<div class="ra-kpi-label">{escape(label)}</div>'
        f'<div class="{value_class}">{escape(value)}</div></div>'
    )


def info_box(text: str) -> None:
    """Muted box with a blue left border for context and hints."""
    st.html(f'<div class="ra-info">{escape(text)}</div>')
