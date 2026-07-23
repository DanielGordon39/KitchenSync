# Instagram Creator Expansion Results

## Completion gate

- Frozen expansion queue: 88 selected and 88 attempted URLs, all unique.
- Active queue: 101 entries representing 100 unique Instagram sources because Phase 1 entries 1 and 2 are duplicates; case 002 was not created.
- Discovery: 8 supplied creators / 16 URLs, then 26 discovered creators / 72 URLs.
- Usable expansion descriptions: 84.
- Acquisition failures: 4, retained in place and not replaced.
- Final offline corpus: 96 accepted cases (84 expansion plus 12 Phase 1).
- Expansion cases: 47/47 complete exact and 37/37 fallback exact.
- Aggregate cases: 57/57 complete coverage, 57/57 complete precision, and 39/39 fallback correctness (all 100%).
- All 12 Phase 1 cases remain exact: 10 complete and 2 fallback.
- Final repository test result: `43 passed` from `uv run pytest`.
- Task edits stayed under `scratch/`. Concurrent/pre-existing non-scratch worktree changes were left untouched.

The 100-source selection target is met. The corpus has 96 usable descriptions because four frozen URLs failed acquisition.

## Creator distribution

Supplied Phase 1 creators, two new URLs each (16 total):

- `joexfitness`: 2
- `jalalsamfit`: 2
- `stealth_health_life`: 2
- `cooklikeimbook`: 2
- `tastyshreds`: 2
- `recipeincaption`: 2
- `vegan_punks`: 2
- `ciaobellaa`: 2

Discovered creators (72 total):

- `_aussiefitness`: 3
- `alexskitchenbangers`: 3
- `amateurprochef`: 3
- `bettercheatmeals`: 3
- `eliya.eats`: 3
- `emthenutritionist`: 3
- `fairfiteats`: 3
- `fit_foodie_lulu`: 3
- `fitfoodiestasia`: 3
- `foodinfivemins`: 3
- `gymhealthu`: 3
- `gymratrecipes`: 2
- `healthysweetsandeats`: 3
- `hunt4shredz`: 3
- `ice.karimcooks`: 3
- `low.carb.love`: 3
- `noahperlofit`: 3
- `panaceapalm`: 3
- `proteinmusclemeals`: 3
- `raziyyz`: 3
- `recipeswith_jess`: 3
- `shredhappens`: 3
- `torinredpath`: 3
- `tracesoats`: 1
- `wannabechefmatt`: 1
- `whatmolly.eats`: 2

## Acquisition failures

- 040 `proteinmusclemeals/p/Da6KJy2la9N/`: carousel child `Da6J-sTtv9_` reported no video formats.
- 057 `gymratrecipes/p/Da6K4ffgafM/`: carousel child `Da6Ked3Bfxe` reported no video formats.
- 058 `gymratrecipes/p/DaoVCQrjgbN/`: carousel child `DaoUvG5uSbm` reported no video formats.
- 068 `noahperlofit/reel/Da6PLkZBN5o/`: Instagram DNS resolution failed on both attempts; acquisition recovered for the next queue item.

## Retained creator-independent rules

- Title evidence: decorated and labeled titles, series/episode forms, title-plus-emoji layouts, title-cased first lines, nearby-yield corroboration, demonstrative subject/action forms, nutrition and generic-heading exclusions, and narrative suffix cleanup.
- Yield evidence: more macro and serving layouts, word-number yields, batch and descriptive serving units, inline ingredient-heading yields, and suppression of ambiguous alternative ranges.
- Ingredient context: unlabeled and component lists, serving/topping groups, emoji bullets, parenthetical hard wraps, optional lines under explicit headings, headed bullet runs before numbered methods, and short unquantified lines inside strong ingredient blocks.
- Instruction context: hard-wrapped numbered steps, compact and keycap numbering, restarted component numbering, trailing unnumbered method steps, temporal prefixes, component prefixes, and common imperative verbs.
- Boundaries: nutrition, promotion, series metadata, pre-yield preambles, post-recipe storage/reheating blocks, and source-wide literal hashtag extraction.

No retained rule uses a creator, handle, shortcode, URL, exact dish name, or exact ingredient phrase.

## Discarded or narrowed attempts

- Broad later-sentence imperative detection captured marketing copy; retained only the locally supported `Simply …` form.
- Unrestricted emoji-title extraction captured long narratives; retained short/title-shaped and corroborated layouts.
- Treating every line in an explicit ingredient candidate as an ingredient regressed case 071; retained only explicit optional lines and narrow local component context.
- Dropping every instruction before a serving cue regressed cases 007 and 052; retained only preamble before both the first yield and first ingredient content.
- Nearby-yield title corroboration initially captured series metadata and an existing descriptive suffix; both received structural guards.
- Same-line emoji title splitting initially broke a title containing an internal emoji; retained only post-emoji narrative lead-ins.

## Expansion outcomes

- 014 `korean-spicy-tofu-stew-meal-prep`: complete-correct
- 015 `banh-cuon`: complete-correct
- 016 `orange-pepper-chicken-rice-bowls`: complete-correct
- 017 `crispy-garlic-parmesan-chicken-wraps`: complete-correct
- 018 `butter-chicken-mac-n-cheese`: fallback-correct
- 019 `slow-cooker-chicken-taco-bowls`: fallback-correct
- 020 `cream-top`: complete-correct
- 021 `untitled-cod-bowl`: fallback-correct
- 022 `protein-buffalo-chicken-sticks`: fallback-correct
- 023 `chick-fil-a-breakfast-burrito-meal-prep-dupe`: fallback-correct
- 024 `one-pan-greek-chicken-rice-bowls`: complete-correct
- 025 `marry-me-salmon`: complete-correct
- 026 `soymaxx-toast`: complete-correct
- 027 `tofu-paratha`: complete-correct
- 028 `coriander-garlic-and-butter-prawns-and-clam`: complete-correct
- 029 `super-speedy-laksa`: complete-correct
- 030 `spicy-chilli-and-cheddar-ramen`: fallback-correct
- 031 `one-pot-chicken-tikka-rice`: fallback-correct
- 032 `tandoori-chicken-rice-bowl`: fallback-correct
- 033 `high-protein-creamy-caramelized-onion-chicken-pasta`: fallback-correct
- 034 `high-protein-creamy-garlic-chicken-and-rice-burritos`: complete-correct
- 035 `grilled-cheese-pepperoni-pizza-chicken-burritos`: complete-correct
- 036 `high-protein-animal-style-smash-burger-bowls`: fallback-correct
- 037 `sticky-korean-bbq-stuffed-sweet-potatoes`: fallback-correct
- 038 `air-fried-crispy-chipotle-honey-chicken-tenders`: fallback-correct
- 039 `chick-fil-a-bbq-chicken-mac-hack`: complete-correct
- 040: acquisition-failure
- 041 `300-calorie-huge-and-massive-crumbl-protein-brookie`: complete-correct
- 042 `hot-korean-beef-rice-and-cucumber-salad-bowl`: complete-correct
- 043 `hawaiian-chicken-and-pineapple-bowl`: complete-correct
- 044 `kansas-city-style-bbq-chicken-bites-and-crispy-potatoes`: complete-correct
- 045 `protein-loaded-sweet-potato-boats`: complete-correct
- 046 `chilli-lime-chicken-with-coconut-rice-and-watermelon-salad`: complete-correct
- 047 `15min-sticky-beef-with-a-smashed-cucumber-salad`: fallback-correct
- 048 `high-protein-chilli-lime-shrimp-bowls`: fallback-correct
- 049 `high-protein-birthday-cake-fluff`: complete-correct
- 050 `easy-high-protein-snack-cookie-dough`: fallback-correct
- 051 `jerk-chicken-fried-rice`: fallback-correct
- 052 `the-best-homemade-carrot-cake`: complete-correct
- 053 `the-best-homemade-tuna-pasta-salad`: fallback-correct
- 054 `jersey-mikes-sub-in-a-tub`: fallback-correct
- 055 `diabetic-friendly-guacamole-chicken-salad`: complete-correct
- 056 `easy-20-minute-crispy-rice-paper-chicken-nuggets`: fallback-correct
- 057: acquisition-failure
- 058: acquisition-failure
- 059 `bacon-cheeseburger-hot-pockets`: fallback-correct
- 060 `waffle-breakfast-sandwiches`: fallback-correct
- 061 `crispy-buffalo-chicken-mac-and-cheese`: fallback-correct
- 062 `roasted-honey-mustard-chicken-and-broccoli`: fallback-correct
- 063 `creamy-tomato-parm-shrimp-orzo-skillet`: fallback-correct
- 064 `biscoff-banana-loaf`: fallback-correct
- 065 `red-thai-curry-chicken-skewers`: complete-correct
- 066 `hot-honey-cajun-beef-folded-wrap`: complete-correct
- 067 `crispy-honey-buffalo-chicken-loaded-fries`: complete-correct
- 068: acquisition-failure
- 069 `the-best-thick-bacon-cheeseburger`: fallback-correct
- 070 `pancakes`: fallback-correct
- 071 `cilantro-jalapeno-chicken-one-pan-meal`: fallback-correct
- 072 `ground-beef-and-eggs-in-15-mins`: complete-correct
- 073 `15-minute-ground-beef-skillet`: complete-correct
- 074 `fluffy-lemon-berry-pancake-bowls`: complete-correct
- 075 `high-protein-mee-goreng`: complete-correct
- 076 `loaded-big-mac-fries`: complete-correct
- 077 `high-protein-chinese-egg-drop-soup`: fallback-correct
- 078 `high-protein-chicken-bacon-ranch-rolls`: fallback-correct
- 079 `healthy-and-easy-high-protein-biscoff-chesecake`: complete-correct
- 080 `creamy-feta-and-chorizo-orzo-salad`: complete-correct
- 081 `creamy-pesto-chicken-wrap`: complete-correct
- 082 `sweet-chilli-chicken-toastie`: complete-correct
- 083 `protein-oreo-mcflurry-dupe`: complete-correct
- 084 `chocolate-protein-rice-cake-bites`: complete-correct
- 085 `protein-snickers-baked-oats`: complete-correct
- 086 `broccoli-pesto-pasta`: complete-correct
- 087 `one-pot-hainanese-inspired-chicken-rice`: complete-correct
- 088 `sticky-honey-chicken-with-charred-peach-salsa`: complete-correct
- 089 `genius-healthy-lava-cake-dessert`: complete-correct
- 090 `roasted-chicken-and-veggie-dinner`: fallback-correct
- 091 `high-protein-cucumber-chicken-salad`: fallback-correct
- 092 `untitled-chocolate-peanut-butter-baked-oats`: fallback-correct
- 093 `creamy-lemon-garlic-chicken-bowls-with-a-creamy-low-cal-mash`: fallback-correct
- 094 `honey-soy-chicken-bakes`: fallback-correct
- 095 `chicken-shawarma-bowls`: complete-correct
- 096 `chicken-pho`: fallback-correct
- 097 `cinnamon-roll-cheesecake-protein-bites`: complete-correct
- 098 `cinnamon-raisin-cottage-cheese-bagels`: complete-correct
- 099 `high-protein-zucchini-sandwich-rounds`: complete-correct
- 100 `crispy-chicken-caesar-pasta-salad`: complete-correct
- 101 `crispy-chicken-caesar-sandwich-prep`: fallback-correct

The frozen expectations remain provisional pending user audit. No additional platform was added.
