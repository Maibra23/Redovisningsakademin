"""Översikt: the recommended next step, repetitions, svit, nivå and XP, the weakest
skills and the last 30 days of activity. A new learner sees the welcome and the
two ways in instead. Layout only; every figure comes from services.profile.
"""

import uuid
from collections.abc import Mapping

import plotly.graph_objects as go
import streamlit as st

from ra.services import learner, practice, profile
from ra.services.views import ChallengeView, NextStep, NextStepView, OverviewView
from ra.ui.components.exercise import exercise_body, forget_instance, stored_result
from ra.ui.i18n import get_lang, t
from ra.ui.pages.lektioner import SELECTED_KEY as LESSON_KEY
from ra.ui.pages.ovningar import SKILL_KEY
from ra.ui.theme import COLORS, info_box, kpi_tile, page_title

CHALLENGE_KEY = "utmaning_aktuell"
CHALLENGE_CONTEXT = "utmaning"
STATE_NAMES = {"ej_paborjad": "Ej påbörjad", "ovar": "Övar", "kompetent": "Kompetent",
               "befast": "Befäst"}


def _choice(title: str, text: str, target: st.Page, link_label: str) -> None:
    with st.container(border=True):
        st.subheader(t(title), anchor=False)
        st.write(t(text))
        st.page_link(target, label=t(link_label), icon=":material/arrow_forward:")


def _welcome(pages: Mapping[str, st.Page]) -> None:
    info_box(t("Här ser du snart ditt nästa steg, dina repetitioner och hur det går. Allt "
               "fylls i när du svarar på dina första övningar."))
    new_col, experienced_col = st.columns(2)
    with new_col:
        _choice("Jag är ny",
                "Börja med grunderna. Lektionerna förklarar varje moment med ett exempel.",
                pages["lektioner"], "Till lektionerna")
    with experienced_col:
        _choice("Jag har erfarenhet", "Gå direkt till övningarna och träna det du behöver.",
                pages["ovningar"], "Till övningarna")


def _go(page: st.Page, key: str | None = None, value: str | None = None) -> None:
    if key is not None:
        st.session_state[key] = value
    st.switch_page(page)


def _next_step(step: NextStepView, due_count: int, pages: Mapping[str, st.Page]) -> None:
    with st.container(border=True):
        st.subheader(t("Nästa steg"), anchor=False)
        if step.kind is NextStep.REPETITION:
            st.write(t("Du har en färdighet att repetera i dag: {0}.", step.title)
                     if due_count == 1 else
                     t("Du har {0} färdigheter att repetera i dag. Börja med {1}.", due_count,
                       step.title))
            if st.button(t("Till repetitionen"), type="primary"):
                _go(pages["repetition"])
        elif step.kind is NextStep.SKILL:
            st.write(t("Din svagaste färdighet just nu är {0}. Öva på den med nya siffror.",
                       step.title))
            if st.button(t("Öva på {0}", step.title), type="primary"):
                _go(pages["ovningar"], SKILL_KEY, step.target_id)
        elif step.kind is NextStep.LESSON:
            st.write(t("Nästa lektion är {0}.", step.title))
            if st.button(t("Till lektionen"), type="primary"):
                _go(pages["lektioner"], LESSON_KEY, step.target_id)
        else:
            st.write(t("Du har gått igenom lektionerna. Bokför en hel månad i simulatorn."))
            if st.button(t("Till simulatorn"), type="primary"):
                _go(pages["simulator"])


def _count(number: int, one: str, many: str) -> str:
    """Singular or plural; both forms are separate texts so each has its English."""
    return t(one, number) if number == 1 else t(many, number)


def _tiles(view: OverviewView) -> None:
    due, streak, level, xp = st.columns(4)
    with due:
        kpi_tile(t("Dagens repetition"), _count(view.due_count, "{0} färdighet", "{0} färdigheter"),
                 "warning" if view.due_count else "default")
    with streak:
        kpi_tile(t("Svit"), _count(view.streak, "{0} dag", "{0} dagar"))
    with level:
        kpi_tile(t("Nivå"), view.level.name)
    with xp:
        kpi_tile(t("XP"), str(view.level.xp))
    if view.level.next_needs_role:
        st.caption(t("Nästa nivå, {0}, kräver också att alla färdigheter för {1} är Kompetent.",
                     view.level.next_name, view.level.next_needs_role))
    elif view.level.next_name:
        st.caption(t("{0} XP kvar till nivån {1}. Längsta svit: {2}.", view.level.xp_to_next,
                     view.level.next_name, _count(view.longest_streak, "{0} dag", "{0} dagar")))


def _weakest(view: OverviewView) -> None:
    st.subheader(t("Svagaste färdigheterna"), anchor=False)
    if not view.weakest:
        st.caption(t("Inga färdigheter övade ännu."))
    for skill in view.weakest:
        share = (t("{0} % rätt bland de senaste", skill.recent_percent)
                 if skill.recent_percent is not None else t("Inga försök ännu"))
        st.write(f"**{skill.skill_id} {skill.name}**  \n"
                 f"{t(STATE_NAMES[skill.state.value])}, {share}")


def _activity(view: OverviewView) -> None:
    st.subheader(t("Aktivitet de senaste 30 dagarna"), anchor=False)
    labels = [day.label for day in view.activity]
    figure = go.Figure([
        go.Bar(name=t("Rätt"), x=labels, y=[d.correct for d in view.activity],
               marker_color=COLORS["success"]),
        go.Bar(name=t("Fel"), x=labels, y=[d.wrong for d in view.activity],
               marker_color=COLORS["danger"]),
    ])
    figure.update_layout(
        barmode="stack", height=260, margin={"l": 10, "r": 10, "t": 10, "b": 10},
        legend={"orientation": "h", "y": 1.12}, font={"family": "Inter"},
        yaxis={"title": t("Antal svar"), "rangemode": "tozero", "dtick": 5},
        xaxis={"type": "category", "tickangle": -45, "nticks": 10},
        plot_bgcolor=COLORS["card_bg"], paper_bgcolor=COLORS["card_bg"])
    st.plotly_chart(figure, config={"displayModeBar": False})


def _open_challenge(index: int | None) -> None:
    st.session_state[CHALLENGE_KEY] = index


def _leave_challenge_item(view: ChallengeView, index: int) -> None:
    item = view.items[index]
    forget_instance(item.exercise_id, item.seed)
    following = index + 1
    st.session_state[CHALLENGE_KEY] = following if following < len(view.items) else None


@st.fragment
def _challenge(learner_id: uuid.UUID, lang: str) -> None:
    st.subheader(t("Dagens utmaning"), anchor=False)
    view = profile.challenge(learner_id, lang)
    if not view.items:
        st.caption(t("Dagens utmaning kommer när övningarna är publicerade."))
        return
    st.caption(t("Fem uppgifter från olika färdigheter, samma för alla den {0}. {1} av {2} "
                 "gjorda, {3} rätt.", view.on, view.done, len(view.items), view.right))
    index = st.session_state.get(CHALLENGE_KEY)
    if index is None:
        first_open = next((i for i, item in enumerate(view.items) if item.right is None), None)
        if first_open is None:
            st.success(t("Du har gjort dagens utmaning. Kom tillbaka i morgon för fem nya."),
                       icon=":material/flag:")
            return
        st.button(t("Starta dagens utmaning") if view.done == 0 else t("Fortsätt utmaningen"),
                  type="primary", on_click=_open_challenge, args=(first_open,))
        return
    item = view.items[index]
    exercise = practice.exercise_view(lang, item.exercise_id, item.seed)
    st.markdown(f"**{t('Uppgift {0} av {1}', index + 1, len(view.items))}: {item.skill_name}**")
    exercise_body(learner_id, exercise, lang, context=CHALLENGE_CONTEXT)
    if stored_result(exercise) is not None:
        last = index + 1 == len(view.items)
        st.button(t("Avsluta utmaningen") if last else t("Nästa uppgift"), type="primary",
                  key=f"utmaning_nasta_{index}", on_click=_leave_challenge_item,
                  args=(view, index))


def render(pages: Mapping[str, st.Page]) -> None:
    lang = get_lang()
    learner_id = learner.get_or_create()
    page_title(t("Hem"), t("Välkommen till Redovisningsakademin"),
               t("Öva svensk bokföring med BAS-kontoplanen och få veta exakt vad som blev fel "
                 "och varför."))
    view = profile.overview(learner_id, lang)
    if not view.has_history:
        _welcome(pages)
        _challenge(learner_id, lang)
        return
    _next_step(view.next_step, view.due_count, pages)
    _tiles(view)
    weak_col, activity_col = st.columns([1, 2])
    with weak_col:
        _weakest(view)
    with activity_col:
        _activity(view)
    _challenge(learner_id, lang)
