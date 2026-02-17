import pytest

pytestmark = [pytest.mark.e2e, pytest.mark.asyncio]


async def test_media_search(e2e, fresh_user):
    result = await e2e.send("what movies are we downloading?", user_id=fresh_user)
    assert "delegate_media" in result.tool_names
    assert result.messages
    assert not result.errors


async def test_memory_roundtrip(e2e, fresh_user):
    r1 = await e2e.send("remember that I love sci-fi movies", user_id=fresh_user)
    assert "remember" in r1.tool_names

    r2 = await e2e.send("what genre do I like?", user_id=fresh_user)
    assert "recall" in r2.tool_names
    assert "sci-fi" in r2.messages[0].lower()


async def test_greeting(e2e, fresh_user):
    result = await e2e.send("hey, how are you?", user_id=fresh_user)
    assert result.messages
    assert not result.tool_names


async def test_interrupt_no_auto_approve(e2e, fresh_user):
    result = await e2e.send("download the matrix", user_id=fresh_user, auto_approve=False)
    if result.interrupt:
        assert result.interrupt["actions"]
    else:
        assert result.messages


async def test_multi_turn_context(e2e, fresh_user):
    r1 = await e2e.send("search for inception movie", user_id=fresh_user)
    assert r1.messages

    r2 = await e2e.send("tell me more about that movie", user_id=fresh_user)
    assert r2.messages
    assert r2.thread_id == r1.thread_id


async def test_schedule_and_list_tasks(e2e, fresh_user):
    r1 = await e2e.send(
        "schedule a task: remind me to check the oven. Schedule it 2 minutes from now.",
        user_id=fresh_user,
    )
    assert "schedule_task" in r1.tool_names
    assert r1.messages
    assert not r1.errors

    r2 = await e2e.send("list my tasks", user_id=fresh_user)
    assert "list_tasks" in r2.tool_names
    assert r2.messages
    assert not r2.errors


async def test_list_tasks_empty(e2e, fresh_user):
    result = await e2e.send("show me my tasks", user_id=fresh_user)
    assert "list_tasks" in result.tool_names
    assert result.messages
    assert not result.errors


async def test_schedule_recurring_task(e2e, fresh_user):
    result = await e2e.send(
        "set up a recurring daily task at 11pm to reflect on today's conversations",
        user_id=fresh_user,
    )
    assert "schedule_task" in result.tool_names
    assert result.messages
    assert not result.errors
