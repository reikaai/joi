DEFAULT_LIMIT = 50


def paginate[T](items: list[T], limit: int = DEFAULT_LIMIT, offset: int = 0) -> tuple[list[T], int, bool]:
    """Apply pagination. Returns (paginated_items, total, has_more)."""
    total = len(items)
    paginated = items[offset : offset + limit]
    has_more = offset + limit < total
    return paginated, total, has_more
