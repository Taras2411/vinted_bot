from aiosqlite import Connection


async def get_or_create_user(
    db: Connection,
    tg_id: int,
    username: str | None = None,
):
    cursor = await db.execute(
        """
        INSERT INTO users (tg_id, username)
        VALUES (?, ?)
        ON CONFLICT(tg_id) DO UPDATE SET
            username = excluded.username
        RETURNING id;
        """,
        (tg_id, username),
    )
    row = await cursor.fetchone()
    await cursor.close()
    print(f"User with tg_id {tg_id} has id {row['id']}")
    await db.commit()
    return row["id"]


async def get_user_by_tg_id(db: Connection, tg_id: int):
    cursor = await db.execute(
        "SELECT * FROM users WHERE tg_id = ?;",
        (tg_id,),
    )
    row = await cursor.fetchone()
    await cursor.close()
    return row

async def get_tg_id_by_user_id(db: Connection, user_id: int):
    cursor = await db.execute(
        "SELECT tg_id FROM users WHERE id = ?;",
        (user_id,),
    )
    row = await cursor.fetchone()
    await cursor.close()
    if row:
        return row["tg_id"]
    return None