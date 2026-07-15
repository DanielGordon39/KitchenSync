from kitchensync.parsing.web import _recipe_from_scraper


class FakeScraper:
    def ingredients(self):
        return ["2 cups chicken stock"]

    def instructions_list(self):
        return ["Simmer the soup."]

    def title(self):
        return "Tomato Soup"

    def yields(self):
        return "4 servings"

    def description(self):
        return "Simple tomato soup."

    def author(self):
        return "KitchenSync Test"

    def site_name(self):
        return "Example Recipes"

    def total_time(self):
        return 45

    def category(self):
        return "Dinner"

    def cuisine(self):
        return "American"

    def keywords(self):
        return ["Soup", "Weeknight Meal"]

    def image(self):
        return "https://example.com/tomato-soup.jpg"


def test_recipe_from_scraper_populates_tags_and_time_estimate():
    recipe = _recipe_from_scraper(
        FakeScraper(),
        source_url="https://example.com/tomato-soup",
    )

    assert recipe.tags == ["dinner", "american", "soup", "weeknight-meal"]
    assert recipe.time_estimate is not None
    assert recipe.time_estimate.base_minutes == 45
    assert recipe.metadata.author == "KitchenSync Test"
    assert recipe.metadata.imported_from == "recipe-scrapers"
    assert len(recipe.metadata.images) == 1
    assert recipe.metadata.images[0].uri == "https://example.com/tomato-soup.jpg"
    assert recipe.metadata.images[0].alt_text == "Tomato Soup"
