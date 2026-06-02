from aiosqlite import Connection

async def add_item(
    db: Connection,
    vinted_id: int,
    title: str,
    price: str | None,
    url: str,
    image_url: str | None,
    brand: str | None,
    created_at: str | None,
    price_amount: float | None = None,
    currency: str | None = None,
):
    # Пытаемся вставить новую запись
    async with db.execute(
        """
        INSERT INTO items (
            vinted_id, title, price, price_amount, currency,
            url, image_url, brand, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(vinted_id) DO NOTHING
        RETURNING id;
        """,
        (vinted_id, title, price, price_amount, currency,
         url, image_url, brand, created_at),
    ) as cursor:
        row = await cursor.fetchone()
    
    if row:
        await db.commit()
        return row["id"]

    # Если запись уже была (ON CONFLICT сработал), получаем существующий id
    async with db.execute(
        "SELECT id FROM items WHERE vinted_id = ?;",
        (vinted_id,),
    ) as cursor:
        row = await cursor.fetchone()
        return row["id"]