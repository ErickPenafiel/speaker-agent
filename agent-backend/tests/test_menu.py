from app.services.menu_service import get_menu_tool
from seed.menu import MENU, seed_menu


async def test_seed_is_idempotent(session, client):
    await seed_menu(session)
    await seed_menu(session)
    r = await client.get("/menu")
    assert r.status_code == 200
    assert len(r.json()) == len(MENU)


async def test_menu_filter_by_category(session, client):
    await seed_menu(session)
    r = await client.get("/menu", params={"category": "bebidas"})
    assert {i["category"] for i in r.json()} == {"bebidas"}


async def test_get_menu_tool_marks_sold_out_and_is_short(session):
    await seed_menu(session)
    text = await get_menu_tool(session, {"category": "parrilla"})
    assert "Anticuchos: agotado" in text
    assert "Lomo a la parrilla, 78 BOB" in text
    assert "\n" not in text


async def test_get_menu_tool_no_results(session):
    await seed_menu(session)
    assert "No encontré" in await get_menu_tool(session, {"query": "pizza"})
