import jmespath
from pydantic import BaseModel


def apply_query[T: BaseModel](
    items: list[T],
    filter_expr: str | None = None,
    sort_by: str | None = None,
    limit: int | None = None,
) -> list[T]:
    """Apply JMESPath filter, sort, and limit to a list of Pydantic models."""
    if not filter_expr and not sort_by and not limit:
        return items

    data = [item.model_dump() for item in items]
    # Support both 'id' and 'index' as unique keys
    key_field = "index" if data and "index" in data[0] else "id"
    key_to_item = {getattr(item, key_field): item for item in items}

    if filter_expr:
        expr = filter_expr if filter_expr.startswith("[") else f"[?{filter_expr}]"
        data = jmespath.search(expr, data) or []

    if sort_by:
        desc = sort_by.startswith("-")
        key = sort_by.lstrip("-")
        data = sorted(data, key=lambda x: x.get(key, 0), reverse=desc)

    if limit and limit > 0:
        data = data[:limit]

    return [key_to_item[d[key_field]] for d in data]
