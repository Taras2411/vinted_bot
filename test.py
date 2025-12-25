# test how get_user_searches works with user_id from get_user_by_tg_id for tg_id 720318208. use connection for main db
import asyncio
from db import init_db, close_db, get_db
from db.repositories import get_user_by_tg_id, get_user_searches
async def test_get_user_searches():
    await init_db()
    db = await get_db()
    try:
        tg_id = 720318208
        user = await get_user_by_tg_id(db, tg_id)
        if user:
            user_id = user['id']
            searches = await get_user_searches(db, user_id)
            searches_list = [dict(row) for row in searches]
            print(f"Searches for user_id {user_id} (tg_id {tg_id}): {searches_list}")
        else:
            print(f"No user found with tg_id {tg_id}")
    finally:
        await close_db()

if __name__ == "__main__":
    asyncio.run(test_get_user_searches())