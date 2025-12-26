from aiosqlite import Connection

async def get_or_create_user(
    db: Connection,
    tg_id: int,
    username: str | None = None,
):
    async with db.execute(
        """
        INSERT INTO users (tg_id, username)
        VALUES (?, ?)
        ON CONFLICT(tg_id) DO UPDATE SET
            username = excluded.username
        RETURNING id;
        """,
        (tg_id, username),
    ) as cursor:
        row = await cursor.fetchone()
    
    await db.commit()
    return row["id"]

async def get_user_by_tg_id(db: Connection, tg_id: int):
    async with db.execute(
        "SELECT * FROM users WHERE tg_id = ?;",
        (tg_id,),
    ) as cursor:
        return await cursor.fetchone()

async def get_tg_id_by_user_id(db: Connection, user_id: int):
    async with db.execute(
        "SELECT tg_id FROM users WHERE id = ?;",
        (user_id,),
    ) as cursor:
        row = await cursor.fetchone()
        if row:
            return row["tg_id"]
    return None