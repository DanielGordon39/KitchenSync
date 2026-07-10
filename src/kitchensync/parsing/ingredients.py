from ingredient_parser import parse_ingredient

from kitchensync.models import Ingredient, Quantity, RecipeIngredient

from .units import is_container_unit, is_measurable_unit, normalize_unit


def parse_recipe_ingredient_line(text: str) -> RecipeIngredient:
    parsed = parse_ingredient(text)

    return RecipeIngredient(
        ingredient=Ingredient(name=_prepared_ingredient_name(parsed) or text),
        quantity=_quantity(parsed),
        preparation=_preparation(parsed),
        notes=[f"raw: {text}"],
    )


def _ingredient_name(parsed) -> str | None:
    names = getattr(parsed, "name", None)
    if not names:
        return None

    first = names[0]
    return getattr(first, "text", None) or str(first)


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


def _is_container_amount(amount) -> bool:
    return is_container_unit(_amount_unit(amount))


def _is_measurable_amount(amount) -> bool:
    return is_measurable_unit(_amount_unit(amount))


def _amount_float(amount) -> float | None:
    quantity = getattr(amount, "quantity", None)
    return float(quantity) if quantity is not None else None


def _amount_unit(amount) -> str | None:
    return normalize_unit(getattr(amount, "unit", None))
