"""Shared regular-expression vocabulary for deterministic social parsing."""

import re


NUMBERED_INSTRUCTION = re.compile(
    r"^(?:\d+[.)](?:\s+|(?=[A-Z]))|\d\ufe0f?\u20e3\s*)"
)
RECIPE_WORD = re.compile(r"\brecipe\b", re.IGNORECASE)
NUTRITION_HEADING = re.compile(
    r"^(?:macros?|nutrition(?:\s+(?:facts|info|information))?)"
    r"(?:\s+per\s+[^:]+)?\s*:?$",
    re.IGNORECASE,
)
NUTRITION_VALUE = re.compile(
    r"^[^\w\d]*(?:only\s+)?"
    r"(?:(protein|carb(?:ohydrate)?s?|fat|calories?|cals?|fiber|fibre|sugar|sodium)"
    r"\s*:?\s*\d|\d[\d,]*(?:\.\d+)?"
    r"(?:\s*[–-]\s*\d[\d,]*(?:\.\d+)?)?\s*(?:(?:calories?|k?cal)\b|"
    r"g\s*(?:protein|carbs?|fat)\b"
    r"(?:\s+(?:per\s+\w+|meal\s+prep))?[^\w\d]*$))",
    re.IGNORECASE,
)
COMPACT_MACROS = re.compile(
    r"^(?:\d+(?:\.\d+)?\s*g[pcf]\s*(?:[|/]\s*)?){2,}[^\w\d]*$",
    re.IGNORECASE,
)
BULLET_ITEM = re.compile(
    r"^(?:[^\w\s*•-]+\s*)?(?P<marker>[-*•])\s*(?P<content>.*)$"
)
BRACKETED_HEADING = re.compile(r"^\[[^\[\]]{1,40}\]$")
INGREDIENT_HEADING = re.compile(
    r"^(?:ingredients?\b(?:\s*\([^)]*\))?|all\s+you\s+need\s+is)\s*:?$",
    re.IGNORECASE,
)
INGREDIENT_FOR_HEADING = re.compile(
    r"^[^\w]*ingredients?\s+for\s+\d+\b.{0,60}$",
    re.IGNORECASE,
)
TIP_LINE = re.compile(r"^tip(?:\s+\d+)?:\s+\S", re.IGNORECASE)
TIP_HEADING = re.compile(r"^(?:important\s+)?tips?\s*:$", re.IGNORECASE)
POST_RECIPE_HEADING = re.compile(
    r"^(?:notes?|(?:freez(?:e|ing)|reheat(?:ing)?)(?:\s+instructions?)?|"
    r"storage(?:\s*&\s*(?:heating|reheating))?(?:\s+instructions?)?)"
    r"\s*[^\w]*$",
    re.IGNORECASE,
)
POST_RECIPE_LINE = re.compile(
    r"^(?:[-*•]\s*)?(?:freeze|from\s+fridge|from\s+frozen|refrigerate)\b",
    re.IGNORECASE,
)
SERIES_METADATA = re.compile(
    r"\bseries\b|\bep(?:isode)?\.?\s*\d+\b",
    re.IGNORECASE,
)
COOK_SETTING = re.compile(
    r"^(?:(?:high|low)\s*:\s*.+\b(?:hours?|minutes?|mins?)\b|"
    r"(?:air\s+fryer|oven)\s*:\s*.*\d+\s*°?\s*[cf]\b.*"
    r"\b(?:minutes?|mins?)\b)",
    re.IGNORECASE,
)
APPLIANCE_DIRECTION = re.compile(
    r"^(?:air\s+fryer|oven)\s*:\s*.*\d+\s*°?\s*[cf]\b.*"
    r"\b(?:minutes?|mins?)\b",
    re.IGNORECASE,
)
IMPERATIVE_START = re.compile(
    r"^(?:(?:(?:a\s+(?:great\s+)?|pro\s+)?tip\b.*?|"
    r"for\s+(?:the\s+)?[^,]{1,30}),\s*|"
    r"(?:in|into)\s+(?:a|the)\s+(?:(?:small|medium|large)\s+)?"
    r"(?:bowl|dish|pan|pot|skillet),?\s+|"
    r"(?:after|before|once|when)\s+[^,]{1,50},\s*|"
    r"(?:finally|meanwhile|next|simply|then(?:\s+simply)?)(?:,\s*|\s+))?"
    r"(?:add|air\s+fry|allow|arrange|assemble|bake|blend|boil|bring|brown|chop|coat|"
    r"combine|cook|cover|crush|dispense|divide|drizzle|finish|fold|form|fry|garnish|heat|"
    r"lay|layer|let|lift|make|marinate|mash|melt|microwave|mix|pat|place|"
    r"oven\s+bake|pour|preheat|refrigerate\s+overnight|reserve|roast|season|serve|simmer|slice|spray|spread|"
    r"soak|spin|spoon|stir|sear|take|throw|toast|top|toss|wake|whisk)\b",
    re.IGNORECASE,
)
INSTRUCTION_HEADINGS = ("directions", "how to", "instructions", "method", "steps")
SERVINGS_CUE = re.compile(
    r"\b(?:makes?|serves?)\s+~?\s*x?\s*\d+\b|"
    r"\b(?:makes?|serves?)\s+(?:one|two|three|four|five|six|seven|eight|"
    r"nine|ten|eleven|twelve)\b|"
    r"\bingredients?\s*\(\s*\d+\s+(?:\w+\s+){0,2}"
    r"(?:batch(?:es)?|serves?|servings?|portions?)\s*\)|"
    r"\bmacros?\s*\(\s*\d+\s+(?:bowls?|serves?|servings?|portions?|pieces?)\s*\)|"
    r"\bservings?\s*:\s*\d+\b|"
    r"\bingredients?\s+for\s+\d+\b|"
    r"\bper\s+\w+\s+of\s+\d+\b|"
    r"\b\d+(?:\s+(?!per\b)\w+){0,2}\s+servings?\b|"
    r"\bper\s+\w+\b.{0,20}\b\d+\s+total\b|"
    r"\b(?:divide|portion|split)\b.{0,100}\b(?:between|into|among)\s+\d+\s+"
    r"(?:meal\s+prep\s+)?(?:bowls?|containers?|plates?|portions?|servings?)\b",
    re.IGNORECASE,
)
SERVINGS_VALUE = re.compile(
    r"\b(?:makes?|serves?)\s+~?\s*x?\s*(?P<first>\d+)\b|"
    r"\bmacros?\s*\(\s*(?P<eighth>\d+)\s+"
    r"(?:bowls?|serves?|servings?|portions?|pieces?)\s*\)|"
    r"\bingredients?\s*\(\s*(?P<ninth>\d+)\s+(?:\w+\s+){0,2}"
    r"(?:batch(?:es)?|serves?|servings?|portions?)\s*\)|"
    r"\bservings?\s*:\s*(?P<fifth>\d+)\b|"
    r"\bingredients?\s+for\s+(?P<sixth>\d+)\b|"
    r"\bper\s+\w+\s+of\s+(?P<seventh>\d+)\b|"
    r"\b(?P<second>\d+)(?:\s+(?!per\b)\w+){0,2}\s+servings?\b|"
    r"\bper\s+\w+\b.{0,20}\b(?P<fourth>\d+)\s+total\b|"
    r"\b(?:divide|portion|split)\b.{0,100}\b(?:between|into|among)\s+"
    r"(?P<third>\d+)\s+(?:meal\s+prep\s+)?"
    r"(?:bowls?|containers?|plates?|portions?|servings?)\b",
    re.IGNORECASE,
)
SERVINGS_WORD_VALUE = re.compile(
    r"\b(?:makes?|serves?)\s+"
    r"(?P<word>one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)\b",
    re.IGNORECASE,
)
SAVE_RECIPE_NAME = re.compile(
    r"\bsave\s+this\s+(?P<name>.+?)\s*[([]?\s*recipe\b",
    re.IGNORECASE,
)
HASHTAG = re.compile(r"#(?P<tag>[\w-]+)")
PROMOTIONAL_TEXT = re.compile(
    r"\b(?:comment|follow(?:ing)?|like\s*&\s*share|"
    r"link(?:ed)?\s+in\s+(?:my\s+)?bio|"
    r"save\s+(?:this|time|money|your\s+life)|"
    r"do\s+not\s+authorize|creator|let\s+me\s+know|"
    r"(?:do(?:n['’]t|\s+not)\s+forget\s+to\s+)?check\s+out|"
    r"printable\s+(?:recipe|version))\b",
    re.IGNORECASE,
)
EXTERNAL_FULL_RECIPE_CUE = re.compile(
    r"\b(?:printable\s+recipe|comment.{0,80}recipe|"
    r"link(?:ed)?\s+in\s+(?:my\s+)?bio)\b",
    re.IGNORECASE,
)
