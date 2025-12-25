from aiosqlite import Connection

async def link_item_to_search(
    db: Connection,
    search_id: int,
    item_id: int,
):
    # Use context manager to ensure the cursor is closed after execution
    async with db.execute(
        """
        INSERT OR IGNORE INTO search_items (search_id, item_id)
        VALUES (?, ?);
        """,
        (search_id, item_id),
    ) as cursor:
        pass  # Execution happens here
    
    # Commit after the cursor (the statement) is closed
    await db.commit()


async def get_unsent_items_for_search(
    db: Connection,
    search_id: int,
):
    async with db.execute(
        """
        SELECT i.*
        FROM items i
        JOIN search_items si ON si.item_id = i.id
        WHERE si.search_id = ?
          AND si.sent = 0;
        """,
        (search_id,),
    ) as cursor:
        # Fetch data while the cursor is open
        rows = await cursor.fetchall()
    
    # Return data after the context manager has closed the cursor
    return rows


async def mark_item_as_sent(
    db: Connection,
    search_id: int,
    item_id: int,
):
    async with db.execute(
        """
        UPDATE search_items
        SET sent = 1,
            sent_at = CURRENT_TIMESTAMP
        WHERE search_id = ?
          AND item_id = ?;
        """,
        (search_id, item_id),
    ) as cursor:
        pass

    # Commit after the cursor is closed to avoid "SQL statements in progress"
    await db.commit()