from pymongo.errors import DuplicateKeyError


def format_duplicate_key_error(exc: DuplicateKeyError) -> str:
    details = getattr(exc, "details", None) or {}
    key_value = details.get("keyValue") or {}

    if key_value:
        field, value = next(iter(key_value.items()))
        return f"A record with {field}={value!r} already exists."

    return "A record with the same unique value already exists."
