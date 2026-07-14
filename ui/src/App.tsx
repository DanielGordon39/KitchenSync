import tomatoPlaceholder from './assets/recipes/tomato-placeholder.png'
import './App.css'

type RecipeCardData = {
  recipe_id: string
  title: string
  image_url: string | null
  description: string | null
  favorite?: boolean
  rating?: number | null
}

function RecipeCard({ recipe }: { recipe: RecipeCardData }) {
  return (
    <article className="recipe-card">
      <img
        className="recipe-card__image"
        src={recipe.image_url ?? tomatoPlaceholder}
        alt=""
      />

      <h2 className="recipe-card__title">{recipe.title}</h2>

      {recipe.favorite && (
        <span
          className="recipe-card__favorite"
          aria-label="Favorite recipe"
        >
          ★
        </span>
      )}

      {recipe.description && (
        <p className="recipe-card__description">
          {recipe.description}
        </p>
      )}

      {recipe.rating !== null && recipe.rating !== undefined && (
        <span
          className="recipe-card__rating"
          aria-label={`Rated ${recipe.rating} out of 5`}
        >
          {recipe.rating} / 5
        </span>
      )}
    </article>
  )
}

const recipes: RecipeCardData[] = [
  {
    recipe_id: 'tomato-soup',
    title: 'Tomato Soup',
    image_url: tomatoPlaceholder,
    description: 'A warm tomato soup for an easy weeknight dinner.',
    favorite: true,
    rating: 4,
  },
  {
    recipe_id: 'tomato-pasta',
    title: 'Tomato Pasta',
    image_url: null,
    description: 'A quick pasta coated in a bright tomato sauce.',
    favorite: false,
    rating: 5,
  },
  {
    recipe_id: 'roasted-tomato-salad',
    title: 'Roasted Tomato Salad',
    image_url: tomatoPlaceholder,
    description: 'Roasted tomatoes served with greens and a simple dressing.',
    rating: null,
  },
]

function App() {
  return (
    <main>
      <section className="recipe-grid" aria-label="Recipes">
        {recipes.map((recipe) => (
          <RecipeCard key={recipe.recipe_id} recipe={recipe} />
        ))}
      </section>
    </main>
  )
}

export default App
