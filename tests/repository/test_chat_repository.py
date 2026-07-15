"""
채팅 리포지토리 통합 테스트 (설계명세서 13.2).

PostgreSQL test database 에서 실행한다. SQLite 와 UUID/timestamptz/cascade
동작이 다를 수 있기 때문이다.
"""
import uuid

import pytest
from sqlmodel import Session

from app.domain.chat.entity.models import Conversation, Message
from app.domain.chat.repository import ConversationRepository
from app.domain.chat.utils import normalize_title
from app.domain.user.entity.models import User

pytestmark = pytest.mark.filterwarnings("ignore::DeprecationWarning")


@pytest.fixture
def repo_and_user():
    """테스트용 사용자 + repository 세팅. 테스트 종료 후 정리."""
    from app.infrastructure.db.connection import engine

    with Session(engine) as s:
        u = User(
            email=f"repo-{uuid.uuid4().hex}@example.com",
            password_hash="x",
            name="Repo Test",
        )
        s.add(u)
        s.commit()
        s.refresh(u)
        repo = ConversationRepository(s)
        yield repo, u, s
        # 정리: cascade 로 message 삭제
        s.exec(
            __import__("sqlmodel").delete(Conversation).where(
                Conversation.user_id == u.id
            )
        )
        s.delete(u)
        s.commit()


def _create_with_message(repo, user, title, content):
    c = repo.create_conversation(user.id, normalize_title(title))
    repo.add_message(c, "user", content)
    return c


def test_create_and_get(repo_and_user):
    repo, user, _ = repo_and_user
    c = repo.create_conversation(user.id, "제목")
    assert c.message_count == 0
    assert repo.get_conversation(c.id, user.id) is not None


def test_ownership_isolation(repo_and_user):
    repo, user, _ = repo_and_user
    c = _create_with_message(repo, user, "제목", "내용")
    other = uuid.uuid4()
    assert repo.get_conversation(c.id, other) is None
    assert repo.list_conversations(other, 10) == []
    assert repo.delete_conversation(c.id, other) is False


def test_add_message_updates_summary(repo_and_user):
    repo, user, _ = repo_and_user
    c = _create_with_message(repo, user, "제목", "첫 메시지")
    assert c.message_count == 1
    assert c.last_message_preview == "첫 메시지"
    repo.add_message(c, "assistant", "AI 응답")
    s = repo_and_user[2]
    s.refresh(c)
    assert c.message_count == 2
    assert c.last_message_preview == "AI 응답"


def test_list_order_last_message_desc(repo_and_user):
    repo, user, _ = repo_and_user
    c1 = _create_with_message(repo, user, "오래된", "old")
    c2 = _create_with_message(repo, user, "최근", "new")
    rows = repo.list_conversations(user.id, 10)
    assert rows[0].id == c2.id
    assert rows[1].id == c1.id


def test_list_uuid_tiebreaker(repo_and_user):
    repo, user, _ = repo_and_user
    # 동일 시각에 메시지 저장 → UUID 보조 정렬
    c1 = repo.create_conversation(user.id, "A")
    c2 = repo.create_conversation(user.id, "B")
    import datetime as _dt

    now = _dt.datetime.now(_dt.timezone.utc)
    repo.add_message(c1, "user", "x", now=now)
    repo.add_message(c2, "user", "y", now=now)
    rows = repo.list_conversations(user.id, 10)
    # id DESC
    assert rows == sorted(rows, key=lambda r: r.id, reverse=True)


def test_delete_cascades_messages(repo_and_user):
    repo, user, _ = repo_and_user
    c = _create_with_message(repo, user, "제목", "내용")
    repo.add_message(c, "assistant", "응답")
    assert len(repo.list_messages(c.id, user.id)) == 2
    assert repo.delete_conversation(c.id, user.id) is True
    assert repo.list_messages(c.id, user.id) == []


def test_cursor_paginates_without_overlap(repo_and_user):
    repo, user, _ = repo_and_user
    for i in range(5):
        _create_with_message(repo, user, f"t{i}", f"c{i}")

    page1 = repo.list_conversations(user.id, limit_plus_one=3)
    assert len(page1) == 3
    from app.domain.chat.utils import encode_cursor, decode_cursor

    last = page1[-1]
    ts, cid = decode_cursor(encode_cursor(last.last_message_at, last.id))
    page2 = repo.list_conversations(
        user.id, limit_plus_one=3, cursor_time=ts, cursor_id=cid
    )
    ids1 = {r.id for r in page1}
    ids2 = {r.id for r in page2}
    assert ids1.isdisjoint(ids2)
    assert len(page2) == 2