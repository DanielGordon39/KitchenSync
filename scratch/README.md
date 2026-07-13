# Scratch

Tracked exploratory scripts for debugging KitchenSync behavior across machines.

Files here are allowed to call live URLs, print output, and help inspect APIs. They are not imported by package code and are not production entrypoints.

Current probe:
- `recipe_input_probe.py`: parse a recipe URL, print the parsed Markdown, and write recipe/ingredient Markdown files under an ignored probe output directory.
