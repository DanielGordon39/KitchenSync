from fractions import Fraction

from ingredient_parser import parse_ingredient

from kitchensync.models import Ingredient, Quantity, RecipeIngredient

from .units import is_container_unit, is_measurable_unit, normalize_unit


CUT_PREPARATIONS = {"cubes", "diced", "strips"}


def project_ingredient_line(text: str) -> dict[str, str | bool | None]:
    """Project a raw line into the fields the recipe editor can represent safely."""
    empty_projection: dict[str, str | bool | None] = {
        "raw_text": text,
        "safe_for_rich": True,
        "quantity_text": None,
        "unit": None,
        "ingredient_name": None,
        "preparation": None,
        "reason": None,
    }
    if not text.strip():
        return empty_projection

    try:
        parsed = parse_ingredient(text)
    except Exception:
        return {
            **empty_projection,
            "safe_for_rich": False,
            "reason": "This line could not be parsed safely.",
        }

    reason = _rich_editor_unsupported_reason(parsed)
    if reason is not None:
        return {
            **empty_projection,
            "safe_for_rich": False,
            "reason": reason,
        }

    amounts = getattr(parsed, "amount", None) or []
    amount = amounts[0] if amounts else None
    return {
        **empty_projection,
        "quantity_text": _editor_quantity_text(amount),
        "unit": _amount_unit(amount) if amount is not None else None,
        "ingredient_name": _ingredient_name(parsed),
        "preparation": _preparation(parsed),
    }


def parse_recipe_ingredient_line(text: str) -> RecipeIngredient:
    parsed = parse_ingredient(text)
    name = _prepared_ingredient_name(parsed) or text
    preparation = _preparation(parsed)

    if preparation is None:
        name, preparation = _split_trailing_preparation(name)

    return RecipeIngredient(
        ingredient=Ingredient(name=name),
        quantity=_quantity(parsed),
        preparation=preparation,
        notes=[f"raw: {text}"],
    )


def _ingredient_name(parsed) -> str | None:
    names = getattr(parsed, "name", None)
    if not names:
        return None

    first = names[0]
    return getattr(first, "text", None) or str(first)


def _rich_editor_unsupported_reason(parsed) -> str | None:
    names = getattr(parsed, "name", None) or []
    amounts = getattr(parsed, "amount", None) or []

    if not names:
        return "No ingredient name could be identified."
    if len(names) > 1:
        return "Multiple ingredients need Raw view."
    if len(amounts) > 1:
        return "Multiple quantities need Raw view."
    if getattr(parsed, "size", None):
        return "Size details need Raw view."
    if getattr(parsed, "comment", None):
        return "Comments such as 'to taste' need Raw view."
    if getattr(parsed, "purpose", None):
        return "Purpose details need Raw view."
    if amounts and getattr(amounts[0], "MULTIPLIER", False):
        return "Multiplier quantities need Raw view."
    return None


def _editor_quantity_text(amount) -> str | None:
    if amount is None:
        return None

    quantity = getattr(amount, "quantity", None)
    if quantity is None:
        return None

    text = _format_quantity(quantity)
    quantity_max = getattr(amount, "quantity_max", None)
    if getattr(amount, "RANGE", False) and quantity_max is not None:
        text = f"{text}-{_format_quantity(quantity_max)}"
    if getattr(amount, "APPROXIMATE", False):
        text = f"about {text}"
    return text


def _format_quantity(value: object) -> str:
    if not isinstance(value, Fraction):
        return str(value)
    if value.denominator == 1:
        return str(value.numerator)

    sign = "-" if value < 0 else ""
    numerator = abs(value.numerator)
    whole, remainder = divmod(numerator, value.denominator)
    if whole and remainder:
        return f"{sign}{whole} {remainder}/{value.denominator}"
    return f"{sign}{remainder}/{value.denominator}"


def _prepared_ingredient_name(parsed) -> str | None:
    name = _ingredient_name(parsed)
    if not name:
        return None

    amounts = getattr(parsed, "amount", None) or []
    if (
        len(amounts) >= 2
        and _is_container_amount(amounts[0])
        and _is_measurable_amount(amounts[1])
    ):
        container_unit = _amount_unit(amounts[0])
        if container_unit in {"can", "cans"}:
            return f"canned {name}"

    return name


def _quantity(parsed) -> Quantity | None:
    amounts = getattr(parsed, "amount", None)
    if not amounts:
        return None

    if (
        len(amounts) >= 2
        and _is_container_amount(amounts[0])
        and _is_measurable_amount(amounts[1])
    ):
        count = _amount_float(amounts[0])
        size = _amount_float(amounts[1])
        if count is not None and size is not None:
            return Quantity(amount=count * size, unit=_amount_unit(amounts[1]))

    first = amounts[0]
    return Quantity(amount=_amount_float(first), unit=_amount_unit(first))


def _preparation(parsed) -> str | None:
    preparation = getattr(parsed, "preparation", None)
    if not preparation:
        return None

    return getattr(preparation, "text", None) or str(preparation)


def _split_trailing_preparation(name: str) -> tuple[str, str | None]:
    pieces = name.rsplit(maxsplit=1)
    if len(pieces) != 2:
        return name, None

    base_name, preparation = pieces
    if preparation.casefold() not in CUT_PREPARATIONS:
        return name, None

    return base_name, preparation


def _is_container_amount(amount) -> bool:
    return is_container_unit(_amount_unit(amount))


def _is_measurable_amount(amount) -> bool:
    return is_measurable_unit(_amount_unit(amount))


def _amount_float(amount) -> float | None:
    quantity = getattr(amount, "quantity", None)
    return float(quantity) if quantity is not None else None


def _amount_unit(amount) -> str | None:
    return normalize_unit(getattr(amount, "unit", None))
