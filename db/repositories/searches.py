from aiosqlite import Connection

async def add_search(
    db: Connection,
    user_id: int,
    title: str,
    vinted_url: str,
):
    async with db.execute(
        """
        INSERT INTO searches (user_id, title, vinted_url)
        VALUES (?, ?, ?)
        RETURNING *;
        """,
        (user_id, title, vinted_url),
    ) as cursor:
        row = await cursor.fetchone()
    
    await db.commit()
    return row

async def get_user_searches(db: Connection, user_id: int):
    async with db.execute(
        """
        SELECT * FROM searches
        WHERE user_id = ? AND active = 1
        ORDER BY created_at DESC;
        """,
        (user_id,),
    ) as cursor:
        return await cursor.fetchall()

async def get_active_searches(db: Connection):
    async with db.execute(
        "SELECT * FROM searches WHERE active = 1;"
    ) as cursor:
        return await cursor.fetchall()

async def deactivate_search(db: Connection, search_id: int):
    async with db.execute(
        "UPDATE searches SET active = 0 WHERE id = ?;",
        (search_id,),
    ) as cursor:
        pass
    await db.commit()

async def activate_search(db: Connection, search_id: int):
    async with db.execute(
        "UPDATE searches SET active = 1 WHERE id = ?;",
        (search_id,),
    ) as cursor:
        pass
    await db.commit()

async def remove_search(db: Connection, search_id: int):
    async with db.execute(
        "DELETE FROM searches WHERE id = ?;",
        (search_id,),
    ) as cursor:
        pass
    await db.commit()