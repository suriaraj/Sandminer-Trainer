from uuid import uuid4

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    decode_refresh_token,
)


def test_access_and_refresh_tokens_are_bound_to_session():
    user_id = uuid4()
    session_id = uuid4()

    access = create_access_token(user_id, session_id)
    refresh = create_refresh_token(user_id, session_id)

    assert decode_access_token(access) == (user_id, session_id)
    assert decode_refresh_token(refresh) == (user_id, session_id)
    assert access != refresh
