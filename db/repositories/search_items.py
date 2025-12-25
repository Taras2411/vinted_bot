from aiosqlite import Connection


async def link_item_to_search(
    db: Connection,
    search_id: int,
    item_id: int,
):
    await db.execute(
        """
        INSERT OR IGNORE INTO search_items (search_id, item_id)
        VALUES (?, ?);
        """,
        (search_id, item_id),
    )
    await db.commit()


async def get_unsent_items_for_search(
    db: Connection,
    search_id: int,
):
    cursor = await db.execute(
        """
        SELECT i.*
        FROM items i
        JOIN search_items si ON si.item_id = i.id
        WHERE si.search_id = ?
          AND si.sent = 0;
        """,
        (search_id,),
    )
    return await cursor.fetchall()


async def mark_item_as_sent(
    db: Connection,
    search_id: int,
    item_id: int,
):
    await db.execute(
        """
        UPDATE search_items
        SET sent = 1,
            sent_at = CURRENT_TIMESTAMP
        WHERE search_id = ?
          AND item_id = ?;
        """,
        (search_id, item_id),
    )
    await db.commit()
