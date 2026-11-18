"""Kompetensprofil: every skill with its state, accuracy, attempts and last practice,
progress toward the two role targets, and the passed exams. Layout only; every
figure comes from services.profile.
"""

import streamlit as st

from ra.services import learner, profile
from ra.services.views import ProfileView
from ra.ui.i18n import get_lang, t
from ra.ui.theme import info_box, kpi_tile, page_title

STATE_NAMES = {"ej_paborjad": "Ej påbörjad", "ovar": "Övar", "kompetent": "Kompetent",
               "befast": "Befäst"}
STATE_ICONS = {"ej_paborjad": "○", "ovar": "◐", "kompetent": "●", "befast": "★"}


def _roles(view: ProfileView) -> None:
    st.subheader(t("Mot rollmålen"), anchor=False)
    for column, role in zip(st.columns(len(view.roles)), view.roles, strict=True):
        with column:
            kpi_tile(t("Mot {0}", role.name),
                     t("{0} av {1} färdigheter", role.done, role.total),
                     "success" if role.done == role.total else "default")
            st.progress(role.done / role.total)
            if role.missing:
                st.caption(t("Kvar till Kompetent: {0}", ", ".join(role.missing)))
            else:
                st.caption(t("Alla färdigheter för rollen är Kompetent eller Befäst."))


def _skills(view: ProfileView) -> None:
    st.subheader(t("Färdigheter"), anchor=False)
    rows = [{
        t("Färdighet"): f"{s.skill_id} {s.name}",
        t("Modul"): s.module_title,
        t("Nivå"): f"{STATE_ICONS[s.state.value]} {t(STATE_NAMES[s.state.value])}",
        t("Rätt bland de senaste"): f"{s.recent_percent} %" if s.recent_percent is not None
        else "",
        t("Försök"): s.total,
        t("Senast övad"): s.last_on or "",
    } for s in view.skills]
    st.dataframe(rows, hide_index=True, width="stretch")
    st.caption(t("Kompetent kräver minst 5 försök och minst 80 % rätt utan tips bland de 8 "
                 "senaste, varav en kontering. Befäst kräver två lyckade repetitioner."))


def _exams(view: ProfileView) -> None:
    st.subheader(t("Godkända prov"), anchor=False)
    if not view.exams:
        st.caption(t("Inga godkända prov ännu. Proven finns under Prov."))
    for exam in view.exams:
        st.write(t("✓ {0}: {1} av {2} rätt ({3} %), godkänt {4}.", exam.title, exam.correct,
                   exam.total, exam.percent, exam.on))


def render() -> None:
    lang = get_lang()
    learner_id = learner.get_or_create()
    page_title(t("Min utveckling"), t("Kompetensprofil"),
               t("Här ser du hur säker du är på varje färdighet och hur nära du är rollmålen."))
    view = profile.competence_profile(learner_id, lang)
    if not view.has_history:
        info_box(t("Din profil fylls i när du svarar på övningar. Varje rättat svar räknas, "
                   "och nivån för en färdighet ändras bara genom svar."))
    _roles(view)
    _skills(view)
    _exams(view)
