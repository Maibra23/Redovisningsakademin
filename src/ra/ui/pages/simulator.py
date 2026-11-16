"""Bokföringssimulatorn: keep the books of Nordvik Kontorsmiljö AB for one month.

Uppdrag: the missions that lead through the month in order, and the month's
summary with the badge once every mission is done.
Inkorg: the documents that have arrived, in date order with their status.
Bokför: the chosen document beside the verifikation grid with series, date and
text; the answer is refused with an explanation when it does not balance.
Rättelse: a booked verifikation is never edited; a new verifikation corrects
it and the link is shown in both directions. Rapporter: the six reports,
recomputed from the stored verifikationer on every run, so they change as soon
as something is booked. Bankavstämning: the kontoutdrag beside the bank account
in the huvudbok; the learner marks the differing lines and books what is
missing. Layout and widgets only; every decision is made in services.simulator.
"""

import datetime as dt
import uuid
from html import escape

import streamlit as st

from ra.services import learner, practice, simulator
from ra.services.views import (
    CompanyView,
    InboxItemView,
    InboxView,
    InputProblem,
    MissionView,
    SimSubmitResult,
    SimVoucherView,
)
from ra.ui.components import sim_reports
from ra.ui.components.document_viewer import KIND_NAMES, document_viewer
from ra.ui.components.feedback_panel import feedback_panel
from ra.ui.components.statement import statement_marker, statement_table
from ra.ui.components.voucher import voucher_grid, voucher_table
from ra.ui.i18n import get_lang, t
from ra.ui.theme import info_box, kpi_tile, page_title

VIEW_KEY = "sim_vy"
LEDGER_KEY = "sim_huvudbok_konto"
MISSIONS_VIEW, INBOX_VIEW = "Uppdrag", "Inkorg"
RECONCILIATION_VIEW, REPORTS_VIEW = "Bankavstämning", "Rapporter"
VIEWS = (MISSIONS_VIEW, INBOX_VIEW, RECONCILIATION_VIEW, REPORTS_VIEW)
RECONCILIATION_RESULT = "avstamning"
MISSION_NAMES = {"klart": "✓ Klart", "pagar": "Pågår", "vantar": "Väntar"}
BANK = 1930
SELECTED_KEY = "sim_dokument"
RESULT_KEY = "sim_resultat"
GRID_ROUND_KEY = "sim_omgang"
STATUS_NAMES = {"ny": "Ny", "bokford": "Bokförd", "rattad": "Rättad"}
PROBLEM_TEXTS = {
    InputProblem.BELOPP_OLASLIGT:
        "Ett belopp kunde inte läsas. Skriv beloppet med siffror, till exempel 1 250,50.",
    InputProblem.KONTO_SAKNAS:
        "En rad har ett belopp men inget konto. Välj ett konto för varje rad med belopp.",
    InputProblem.BADA_SIDOR:
        "En rad har belopp i både debet och kredit. Skriv varje belopp på en egen rad.",
    InputProblem.TOMT_SVAR: "Verifikationen har inga rader ännu.",
    InputProblem.TEXT_SAKNAS:
        "Verifikationen saknar text. Skriv kort vad affärshändelsen gäller.",
    InputProblem.DATUM_UTANFOR: "Datumet ligger utanför månaden du bokför.",
    InputProblem.REDAN_BOKFORD:
        "Dokumentet är redan bokfört. Rätta verifikationen i stället för att bokföra igen.",
    InputProblem.INTE_I_INKORGEN: "Dokumentet finns inte i inkorgen ännu.",
    InputProblem.FOR_MANGA:
        "Du har nått gränsen för antalet verifikationer. Återställ simulatorn för att börja om.",
}


def _company(company: CompanyView) -> None:
    with st.expander(t("Om företaget och redovisningsvalen"), expanded=False):
        st.write(company.description)
        st.caption(t("Organisationsnummer {0}. Momsregistreringsnummer {1}. Du bokför {2}.",
                     company.orgnr, company.vat_number, company.month))
        for choice in company.choices:
            st.markdown(f"- {choice}")
        st.caption(t("Företaget, personerna och alla nummer är påhittade."))


def _status(item: InboxItemView) -> str:
    status = t(STATUS_NAMES[item.status])
    if item.correct is None:
        return status
    return f"{status}, {t('✓ Rätt') if item.correct else t('✗ Fel')}"


def _inbox_table(inbox: InboxView) -> None:
    head = "".join(f"<th>{escape(t(h))}</th>"
                   for h in ("Datum", "Dokument", "Motpart", "Status", "Verifikation"))
    body = "".join(
        f"<tr><td>{escape(i.date)}</td><td>{escape(i.title)}</td>"
        f"<td>{escape(i.counterparty)}</td><td>{escape(_status(i))}</td>"
        f"<td>{escape(', '.join(i.vouchers))}</td></tr>"
        for i in inbox.items)
    st.html(f'<table class="ra-table"><tr>{head}</tr>{body}</table>')


def _choose(inbox: InboxView) -> InboxItemView:
    items = {i.event_id: i for i in inbox.items}
    if st.session_state.get(SELECTED_KEY) not in items:
        first_new = next((i.event_id for i in inbox.items if i.status == "ny"),
                         inbox.items[-1].event_id)
        st.session_state[SELECTED_KEY] = first_new
    chosen = st.selectbox(
        t("Öppna dokument"), list(items), key=SELECTED_KEY,
        format_func=lambda i: f"{items[i].date}, {items[i].title} ({_status(items[i])})")
    return items[chosen]


def _show_problems(result: SimSubmitResult) -> None:
    for problem in result.problems:
        if problem is not InputProblem.OBALANS:
            st.warning(t(PROBLEM_TEXTS[problem]), icon=":material/edit:")
    if InputProblem.OBALANS in result.problems and result.totals is not None:
        st.error(t("Verifikationen balanserar inte: summa debet {0} och summa kredit {1} "
                   "skiljer sig med {2}. Ett bokföringsprogram tar inte emot en verifikation "
                   "som inte balanserar, så ingenting har bokförts.",
                   result.totals.total_debet, result.totals.total_kredit,
                   result.totals.difference), icon=":material/block:")


def _show_result(result: SimSubmitResult) -> None:
    if result.feedback is None:
        return
    st.success(t("Bokfört som verifikation {0}.", result.voucher_label),
               icon=":material/check:")
    feedback_panel(result.feedback)
    if result.attempt_no > 1:
        st.caption(t("Rättelser ger ingen XP. Totalt har du {0} XP.", result.total_xp))
    else:
        st.caption(t("Du fick {0} XP. Totalt har du {1} XP.", result.xp, result.total_xp))


def _round() -> int:
    return st.session_state.setdefault(GRID_ROUND_KEY, 0)


def _entry_fields(prefix: str, default_date: dt.date, default_text: str,
                  company: CompanyView) -> tuple[dt.date, str]:
    series, day, text = st.columns([1, 2, 4])
    series.text_input(t("Serie"), value="A", disabled=True, key=f"{prefix}_serie",
                      help=t("Nordvik bokför allt i en verifikationsserie, A."))
    on_date = day.date_input(t("Datum"), value=default_date, min_value=company.first_on,
                             max_value=company.last_on, format="YYYY-MM-DD",
                             key=f"{prefix}_datum")
    entry_text = text.text_input(t("Text"), value=default_text, key=f"{prefix}_text")
    return on_date, entry_text


def _book(learner_id: uuid.UUID, item: InboxItemView, company: CompanyView, lang: str) -> None:
    prefix = f"sim_{item.event_id}_{_round()}"
    on_date, text = _entry_fields(prefix, item.on, item.title, company)
    rows = voucher_grid(f"{prefix}_grid", practice.account_options())
    if st.button(t("Bokför"), type="primary", key=f"{prefix}_bokfor"):
        result = simulator.submit(learner_id, item.event_id, rows, on_date, text, lang)
        if result.problems:
            _show_problems(result)
            return
        st.session_state.setdefault(RESULT_KEY, {})[item.event_id] = result
        st.session_state[GRID_ROUND_KEY] = _round() + 1
        st.rerun()


def _voucher_card(view: SimVoucherView) -> None:
    """A booked verifikation; its text was typed by the learner, so it is escaped."""
    links = []
    if view.corrects:
        links.append(t("Rättar verifikation {0}.", view.corrects))
    if view.corrected_by:
        links.append(t("Rättas av verifikation {0}.", ", ".join(view.corrected_by)))
    link_html = "".join(f'<p class="ra-muted">{escape(link)}</p>' for link in links)
    st.html(f"<p><strong>{escape(t('Verifikation {0}', view.label))}</strong>, "
            f"{escape(view.date)}: {escape(view.text)}</p>{link_html}")
    voucher_table(view.voucher)


def _correct(learner_id: uuid.UUID, item: InboxItemView, booked: list[SimVoucherView],
             company: CompanyView, lang: str) -> None:
    st.subheader(t("Rättelse"), anchor=False)
    st.caption(t("En bokförd verifikation får inte ändras. Du rättar den med en ny "
                 "verifikation som hänvisar till den gamla, till exempel genom att vända den "
                 "felaktiga och bokföra rätt, eller genom att bokföra bara skillnaden."))
    labels = {v.voucher_id: v.label for v in booked if v.voucher_id is not None}
    target = st.selectbox(t("Verifikation att rätta"), list(labels),
                          format_func=lambda i: labels[i], key=f"sim_{item.event_id}_mal")
    prefix = f"sim_{item.event_id}_ratt_{_round()}"
    on_date, text = _entry_fields(prefix, item.on, t("Rättelse av {0}", labels[target]),
                                  company)
    rows = voucher_grid(f"{prefix}_grid", practice.account_options())
    if st.button(t("Bokför rättelsen"), type="primary", key=f"{prefix}_bokfor"):
        result = simulator.correct(learner_id, target, rows, on_date, text, lang)
        if result.problems:
            _show_problems(result)
            return
        st.session_state.setdefault(RESULT_KEY, {})[item.event_id] = result
        st.session_state[GRID_ROUND_KEY] = _round() + 1
        st.rerun()


def _open(event_id: str) -> None:
    st.session_state[SELECTED_KEY] = event_id


@st.fragment
def _workspace(learner_id: uuid.UUID, item: InboxItemView, next_new: str | None,
               company: CompanyView, lang: str) -> None:
    document_col, entry_col = st.columns([5, 6], gap="large")
    with document_col:
        document_viewer(simulator.document(learner_id, item.event_id))
    with entry_col:
        if item.status == "ny":
            st.subheader(t("Bokför"), anchor=False)
            _book(learner_id, item, company, lang)
            return
        booked = [v for v in simulator.vouchers(learner_id) if v.event_id == item.event_id]
        for view in booked:
            _voucher_card(view)
        result = st.session_state.get(RESULT_KEY, {}).get(item.event_id)
        if result is not None:
            _show_result(result)
        if next_new is not None:
            st.button(t("Nästa dokument"), type="primary", key=f"sim_nasta_{item.event_id}",
                      on_click=_open, args=(next_new,))
        _correct(learner_id, item, booked, company, lang)


def _inbox(learner_id: uuid.UUID, company: CompanyView, lang: str) -> None:
    inbox = simulator.inbox(learner_id)
    if inbox.done:
        info_box(t("Alla dokument för {0} är bokförda. Fortsätt med rapporterna och "
                   "månadens avslut.", company.month))
    else:
        st.write(t("Simulatorns datum: {0}. Nya dokument kommer när du har bokfört alla "
                   "dokument fram till dess. {1} dokument har inte kommit än.",
                   inbox.current_day, inbox.waiting))
    _inbox_table(inbox)
    item = _choose(inbox)
    st.caption(t("Underlag: {0}. Motpart: {1}.", t(KIND_NAMES.get(item.kind, item.kind)),
                 item.counterparty))
    next_new = next((i.event_id for i in inbox.items if i.status == "ny"), None)
    _workspace(learner_id, item, next_new, company, lang)


def _goto(view: str, event_id: str | None = None) -> None:
    st.session_state[VIEW_KEY] = view
    if event_id is not None:
        st.session_state[SELECTED_KEY] = event_id


def _mission_row(mission: MissionView) -> None:
    text_col, action_col = st.columns([5, 2], vertical_alignment="center")
    with text_col:
        progress = (t("{0} av {1} dokument rätt bokförda.", mission.done, mission.total)
                    if not mission.reconciliation else "")
        st.html(f"<p><strong>{escape(mission.title)}</strong> "
                f"({escape(t(MISSION_NAMES[mission.status]))})</p>"
                f'<p class="ra-muted">{escape(mission.description)} {escape(progress)}</p>')
    with action_col:
        if mission.reconciliation and mission.status == "pagar":
            st.button(t("Stäm av banken"), key=f"sim_uppdrag_{mission.mission_id}",
                      on_click=_goto, args=(RECONCILIATION_VIEW,), width="stretch")
        elif mission.next_event is not None:
            st.button(t("Öppna nästa dokument"), key=f"sim_uppdrag_{mission.mission_id}",
                      on_click=_goto, args=(INBOX_VIEW, mission.next_event), width="stretch")


def _summary(learner_id: uuid.UUID, lang: str) -> None:
    summary = simulator.month_summary(learner_id, lang)
    if not summary.complete:
        return
    st.subheader(t("Månaden är avslutad"), anchor=False)
    if summary.badge:
        st.success(t("Märke: Månaden avslutad. Du har bokfört, stämt av och avslutat hela "
                     "månaden."), icon=":material/workspace_premium:")
    income_col, balance_col = st.columns(2, gap="large")
    with income_col:
        sim_reports.income_statement(summary.income)
    with balance_col:
        sim_reports.balance_sheet(summary.balance)
    st.subheader(t("Träffsäkerhet per färdighet"), anchor=False)
    st.caption(t("Andelen dokument du bokförde rätt på första försöket, innan någon rättelse."))
    columns = st.columns(3)
    for index, skill in enumerate(summary.skills):
        with columns[index % 3]:
            kpi_tile(f"{skill.skill_id} {skill.name}",
                     t("{0} % ({1} av {2})", skill.percent, skill.correct, skill.total),
                     "success" if skill.percent >= 80 else "warning")


def _restart(learner_id: uuid.UUID) -> None:
    with st.expander(t("Börja om med nya siffror")):
        st.caption(t("Du får en ny månad för samma företag med nya belopp. Det du har bokfört "
                     "hittills sparas men visas inte längre."))
        if st.button(t("Börja om"), key="sim_borja_om"):
            simulator.reset(learner_id)
            for key in (SELECTED_KEY, RESULT_KEY):
                st.session_state.pop(key, None)
            st.session_state[GRID_ROUND_KEY] = _round() + 1
            st.rerun()


def _missions(learner_id: uuid.UUID, lang: str) -> None:
    group = None
    for mission in simulator.missions(learner_id):
        if mission.group != group:
            group = mission.group
            st.subheader(group, anchor=False)
        _mission_row(mission)
    _summary(learner_id, lang)
    _restart(learner_id)


def _reconciliation(learner_id: uuid.UUID, company: CompanyView, lang: str) -> None:
    view = simulator.reconciliation(learner_id)
    if not view.ready:
        info_box(t("Bokför först alla dokument som rör företagskontot. Sedan kan du jämföra "
                   "kontoutdraget med bankkontot."))
        return
    statement_col, ledger_col = st.columns(2, gap="large")
    with statement_col:
        st.subheader(t("Kontoutdrag"), anchor=False)
        st.caption(t("Ingående saldo {0}. Utgående saldo {1}.", view.statement_opening,
                     view.statement_closing))
        marked = statement_marker("sim_avst_markera", view.statement)
    with ledger_col:
        st.subheader(t("Bankkontot i huvudboken"), anchor=False)
        st.caption(t("1930 Företagskonto, utgående balans {0}.", view.ledger_closing))
        statement_table(view.ledger)
    if view.complete:
        st.success(t("Banken är avstämd: bankkontot och kontoutdraget har samma saldo, {0}.",
                     view.ledger_closing), icon=":material/check:")
    else:
        st.warning(t("Skillnad mellan kontoutdraget och bankkontot: {0}. Markera raderna som "
                     "skiljer sig och bokför det som saknas.", view.difference),
                   icon=":material/compare_arrows:")
    for booked in view.booked:
        _voucher_card(booked)
    result = st.session_state.get(RESULT_KEY, {}).get(RECONCILIATION_RESULT)
    if result is not None:
        _show_result(result)
    if view.complete:
        return
    st.subheader(t("Bokför avstämningen"), anchor=False)
    prefix = f"sim_avst_{_round()}"
    on_date, text = _entry_fields(prefix, view.last_on, t("Bankavstämning"), company)
    rows = voucher_grid(f"{prefix}_grid", practice.account_options())
    if st.button(t("Bokför avstämningen"), type="primary", key=f"{prefix}_bokfor"):
        result = simulator.reconcile(learner_id, marked, rows, on_date, text, lang)
        if result.problems:
            _show_problems(result)
            return
        st.session_state.setdefault(RESULT_KEY, {})[RECONCILIATION_RESULT] = result
        st.session_state[GRID_ROUND_KEY] = _round() + 1
        st.rerun()


def _reports(learner_id: uuid.UUID) -> None:
    reports = simulator.reports(learner_id)
    tabs = st.tabs([t("Verifikationslista"), t("Huvudbok"), t("Råbalans"),
                    t("Resultaträkning"), t("Balansräkning"), t("Momsrapport")])
    with tabs[0]:
        sim_reports.voucher_list(reports.vouchers)
    with tabs[1]:
        accounts = {a.number: a for a in reports.ledger}
        default = list(accounts).index(BANK) if BANK in accounts else 0
        number = st.selectbox(t("Konto"), list(accounts), index=default, key=LEDGER_KEY,
                              format_func=lambda n: f"{n} {accounts[n].name}")
        sim_reports.ledger_account(accounts[number])
    with tabs[2]:
        sim_reports.trial_balance(reports.trial_balance)
    with tabs[3]:
        sim_reports.income_statement(reports.income)
    with tabs[4]:
        sim_reports.balance_sheet(reports.balance)
    with tabs[5]:
        sim_reports.vat_report(reports.vat)


def render() -> None:
    lang = get_lang()
    learner_id = learner.get_or_create()
    page_title(t("Praktik"), t("Bokföringssimulatorn"),
               t("Du är redovisningsansvarig på Nordvik Kontorsmiljö AB och bokför en hel "
                 "månad."))
    company = simulator.start(learner_id)
    _company(company)
    st.session_state.setdefault(VIEW_KEY, MISSIONS_VIEW)
    view = st.segmented_control(t("Visa"), VIEWS, key=VIEW_KEY, format_func=t) or MISSIONS_VIEW
    if view == INBOX_VIEW:
        _inbox(learner_id, company, lang)
    elif view == RECONCILIATION_VIEW:
        _reconciliation(learner_id, company, lang)
    elif view == REPORTS_VIEW:
        _reports(learner_id)
    else:
        _missions(learner_id, lang)
