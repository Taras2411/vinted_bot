from aiosqlite import Connection


async def add_search(
    db: Connection,
    user_id: int,
    title: str,
    vinted_url: str,
):
    cursor = await db.execute(
        """
        INSERT INTO searches (user_id, title, vinted_url)
        VALUES (?, ?, ?)
        RETURNING *;
        """,
        (user_id, title, vinted_url),
    )
    row = await cursor.fetchone()
    await cursor.close()
    await db.commit()
    return row


async def get_user_searches(db: Connection, user_id: int):
    cursor = await db.execute(
        """
        SELECT * FROM searches
        WHERE user_id = ? AND active = 1
        ORDER BY created_at DESC;
        """,
        (user_id,),
    )
    rows = await cursor.fetchall()
    await cursor.close()
    return rows


async def get_active_searches(db: Connection):
    cursor = await db.execute(
        """
        SELECT * FROM searches
        WHERE active = 1;
        """
    )
    rows = await cursor.fetchall()
    await cursor.close()
    return rows


async def deactivate_search(db: Connection, search_id: int):
    cursor = await db.execute(
        "UPDATE searches SET active = 0 WHERE id = ?;",
        (search_id,),
    )
    await cursor.close()
    await db.commit()

async def activate_search(db: Connection, search_id: int):
    cursor = await db.execute(
        "UPDATE searches SET active = 1 WHERE id = ?;",
        (search_id,),
    )
    await cursor.close()
    await db.commit()

async def remove_search(db: Connection, search_id: int):
    cursor = await db.execute(
        "DELETE FROM searches WHERE id = ?;",
        (search_id,),
    )
    await cursor.close()
    await db.commit()
