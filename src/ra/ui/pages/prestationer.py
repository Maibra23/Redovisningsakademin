"""Prestationer: the seven märken and the nivåer with XP. Layout only; the märken are
derived by services.profile each time the page loads."""

import streamlit as st

from ra.services import learner, profile
from ra.services.views import AchievementsView
from ra.ui.i18n import get_lang, t
from ra.ui.theme import kpi_tile, page_title


def _badges(view: AchievementsView) -> None:
    st.subheader(t("Märken"), anchor=False)
    st.caption(t("{0} av {1} märken", sum(b.earned for b in view.badges), len(view.badges)))
    columns = st.columns(2)
    for index, badge in enumerate(view.badges):
        with columns[index % 2], st.container(border=True):
            mark = "★" if badge.earned else "☆"
            st.markdown(f"**{mark} {badge.name}**")
            st.write(badge.description)
            st.caption(t("Uppnått") if badge.earned else t("Inte uppnått ännu"))


def _levels(view: AchievementsView) -> None:
    st.subheader(t("Nivå och XP"), anchor=False)
    level, xp = st.columns(2)
    with level:
        kpi_tile(t("Nivå"), view.level.name, "success")
    with xp:
        kpi_tile(t("XP"), str(view.level.xp))
    if view.level.next_name and view.level.xp_to_next is not None:
        next_row = next(r for r in view.levels if r.name == view.level.next_name)
        st.progress(min(1.0, view.level.xp / next_row.min_xp),
                    text=t("{0} XP kvar till nivån {1}.", view.level.xp_to_next,
                           view.level.next_name))
    if view.level.next_needs_role:
        st.caption(t("Nästa nivå, {0}, kräver också att alla färdigheter för {1} är Kompetent.",
                     view.level.next_name, view.level.next_needs_role))
    rows = [{t("Nivå"): f"{'✓' if row.reached else '○'} {row.name}",
             t("XP från"): row.min_xp,
             t("Kräver Kompetent i"): row.role or ""} for row in view.levels]
    st.dataframe(rows, hide_index=True, width="stretch")
    st.caption(t("Du får XP för rätta svar: full XP utan tips på första försöket, halv XP med "
                 "tips. Ett fel svar och ett nytt försök på samma uppgift ger ingen XP."))


def render() -> None:
    lang = get_lang()
    learner_id = learner.get_or_create()
    page_title(t("Min utveckling"), t("Prestationer"),
               t("Märken och nivåer visar vad du har visat att du kan."))
    view = profile.achievements(learner_id, lang)
    _badges(view)
    _levels(view)
