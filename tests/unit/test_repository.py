from app.db.repository import ConversationRepository


def test_create_and_fetch_conversation(db_session):
    repo = ConversationRepository(db_session)
    convo = repo.create_conversation(tech_name="Alice")
    assert convo.id
    assert convo.tech_name == "Alice"
    fetched = repo.get_conversation(convo.id)
    assert fetched.id == convo.id


def test_append_messages_in_order(db_session):
    repo = ConversationRepository(db_session)
    convo = repo.create_conversation(tech_name="Bob")
    m1 = repo.add_message(convo.id, role="user", content={"type": "text", "text": "hi"})
    m2 = repo.add_message(convo.id, role="assistant", content={"type": "model_response", "text": "hello", "citations": []})
    msgs = repo.list_messages(convo.id)
    assert [m.id for m in msgs] == [m1.id, m2.id]


def test_list_conversations_paginated(db_session):
    repo = ConversationRepository(db_session)
    for name in ["A", "B", "C"]:
        repo.create_conversation(tech_name=name)
    page = repo.list_conversations(limit=2, offset=0)
    assert len(page) == 2
