from aiosqlite import Connection

async def add_item(
    db: Connection,
    vinted_id: int,
    title: str,
    price: int,
    url: str,
    image_url: str | None,
    brand: str | None,
    created_at: str | None,
):
    # 1. Attempt the INSERT
    row = None
    async with db.execute(
        """
        INSERT INTO items (
            vinted_id, title, price, url, image_url, brand, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(vinted_id) DO NOTHING
        RETURNING id;
        """,
        (vinted_id, title, price, url, image_url, brand, created_at),
    ) as cursor:
        row = await cursor.fetchone()
    
    # The cursor is now closed automatically. 
    # We can now safely commit or start a new operation.

    if row:
        await db.commit()
        return row["id"]

    # 2. If row was None (Conflict), fetch the existing ID
    async with db.execute(
        "SELECT id FROM items WHERE vinted_id = ?;",
        (vinted_id,),
    ) as cursor:
        row = await cursor.fetchone()
    
    # Cursor is closed again here before returning
    return row["id"] if row else None