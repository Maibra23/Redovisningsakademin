"""Anonymous learner identified by a sparkod in the page address.

The sparkod is a random 128 bit code. Only its SHA 256 hash is stored, so
the database alone cannot be used to open anyone's progress.
"""

import hashlib
import re
import secrets
import uuid

import streamlit as st

from ra.storage import queries
from ra.storage.db import new_session

CODE_PARAM = "kod"
CODE_BYTES = 16  # 128 bits
CODE_PATTERN = re.compile(r"^[A-Za-z0-9_-]{22}$")  # token_urlsafe(16) is 22 characters
SESSION_LEARNER_KEY = "learner_id"
SESSION_CODE_KEY = "sparkod"


def hash_code(code: str) -> str:
    return hashlib.sha256(code.encode("ascii")).hexdigest()


def _code_from_address() -> str | None:
    code = st.query_params.get(CODE_PARAM)
    return code if code and CODE_PATTERN.fullmatch(code) else None


def _load_or_create(code: str | None) -> tuple[uuid.UUID, str]:
    """Learner for ``code``; a new code and learner when it is missing or unknown."""
    with new_session() as session, session.begin():
        if code is not None:
            learner = queries.find_learner_by_hash(session, hash_code(code))
            if learner is not None:
                queries.touch_learner(session, learner.id)
                return learner.id, code
        new_code = secrets.token_urlsafe(CODE_BYTES)
        learner = queries.create_learner(session, hash_code(new_code))
        return learner.id, new_code


def get_or_create() -> uuid.UUID:
    """Learner id for this visit; writes the sparkod into the address.

    The database is read once per browser session; later reruns use the id
    kept in session state as long as the address still holds the same code.
    """
    code = _code_from_address()
    if code is not None and code == st.session_state.get(SESSION_CODE_KEY):
        return st.session_state[SESSION_LEARNER_KEY]
    learner_id, code = _load_or_create(code)
    st.session_state[SESSION_LEARNER_KEY] = learner_id
    st.session_state[SESSION_CODE_KEY] = code
    if st.query_params.get(CODE_PARAM) != code:
        st.query_params[CODE_PARAM] = code
    return learner_id


def reset_simulator(learner_id: uuid.UUID) -> None:
    """Remove the learner's simulator verifikationer so the simulator starts over."""
    with new_session() as session, session.begin():
        queries.delete_sim_vouchers(session, learner_id)


def delete_all(learner_id: uuid.UUID) -> None:
    """Delete the learner and all progress; the next run creates a new learner."""
    with new_session() as session, session.begin():
        queries.delete_learner(session, learner_id)
    for key in (SESSION_LEARNER_KEY, SESSION_CODE_KEY):
        st.session_state.pop(key, None)
    st.query_params.pop(CODE_PARAM, None)
