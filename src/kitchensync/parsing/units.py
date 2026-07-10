CONTAINER_UNITS = {
    "bag",
    "bags",
    "bottle",
    "bottles",
    "box",
    "boxes",
    "can",
    "cans",
    "jar",
    "jars",
    "package",
    "packages",
    "pkg",
    "pkgs",
}

MEASURABLE_UNITS = {
    "cup",
    "cups",
    "fluid_ounce",
    "fluid_ounces",
    "g",
    "gram",
    "grams",
    "kg",
    "kilogram",
    "kilograms",
    "lb",
    "lbs",
    "liter",
    "liters",
    "milliliter",
    "milliliters",
    "ml",
    "ounce",
    "ounces",
    "oz",
    "pound",
    "pounds",
    "quart",
    "quarts",
    "tablespoon",
    "tablespoons",
    "teaspoon",
    "teaspoons",
}


def normalize_unit(unit: object) -> str | None:
    if not unit:
        return None

    return str(unit).lower().replace(" ", "_")


def is_container_unit(unit: object) -> bool:
    return normalize_unit(unit) in CONTAINER_UNITS


def is_measurable_unit(unit: object) -> bool:
    return normalize_unit(unit) in MEASURABLE_UNITS
