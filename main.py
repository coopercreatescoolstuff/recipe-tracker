from drafter import *
from dataclasses import dataclass

# Constants (allowed: no global variables, but constants are fine)
CATEGORIES = ["Breakfast", "Lunch", "Dinner", "Dessert", "Snack"]
FILTER_CATEGORIES = ["All"] + CATEGORIES
HIGH_PROTEIN_GRAMS = 30.0


@dataclass
class Recipe:
    name: str
    category: str
    servings: int
    ingredients: str
    instructions: str
    cost: float
    macros: list[float]  # [protein, carbs, fat] in grams
    favorite: bool


@dataclass
class State:
    recipes: list[Recipe]
    message: str
    selected: int
    category_filter: str
    favorites_only: bool


def to_float(text: str) -> float:
    """Convert text to a float, or return -1.0 if it is not a number."""
    cleaned = text.strip()
    if cleaned.replace(".", "", 1).isdigit():
        return float(cleaned)
    return -1.0


def matching_recipes(state: State) -> list[Recipe]:
    """Loop over every recipe and keep the ones that match the current filters."""
    matches = []
    for recipe in state.recipes:
        category_ok = state.category_filter == "All" or recipe.category == state.category_filter
        favorite_ok = (not state.favorites_only) or recipe.favorite
        if category_ok and favorite_ok:
            matches.append(recipe)
    return matches


# ---------------------------------------------------------------- index
@route
def index(state: State) -> Page:
    shown = matching_recipes(state)
    content = [Header("Recipe Tracker", 1)]
    if state.message != "":
        content.append(state.message)
        content.append(LineBreak())

    content.append(f"Showing: {state.category_filter}" + (" (favorites only)" if state.favorites_only else ""))
    content.append(Header("Recipe List", 2))

    if len(shown) == 0:
        content.append("No recipes to show yet.")
    else:
        names = []
        for recipe in shown:
            star = "★ " if recipe.favorite else ""
            content.append(f"• {star}{recipe.name} ({recipe.category})")
            content.append(LineBreak())
            names.append(recipe.name)
        content.append("Choose recipe: ")
        content.append(SelectBox("chosen_name", names, names[0]))
        content.append(Button("View", view_recipe))

    content.append(LineBreak())
    content.append(Button("Add", add_recipe))
    content.append(Button("Filter", filter_page))
    content.append(Button("Stats", stats_page))
    return Page(state, content)


# ---------------------------------------------------------------- add / save
@route
def add_recipe(state: State) -> Page:
    return Page(state, [
        Header("Add Recipe", 1),
        state.message,
        "Name:", TextBox("name", ""), LineBreak(),
        "Category:", SelectBox("category", CATEGORIES, CATEGORIES[0]), LineBreak(),
        "Servings:", TextBox("servings", "1"), LineBreak(),
        "Cost ($):", TextBox("cost", "0"), LineBreak(),
        "Ingredients:", LineBreak(), TextArea("ingredients", ""), LineBreak(),
        "Instructions:", LineBreak(), TextArea("instructions", ""), LineBreak(),
        "Protein (g):", TextBox("protein", "0"), LineBreak(),
        "Carbs (g):", TextBox("carbs", "0"), LineBreak(),
        "Fat (g):", TextBox("fat", "0"), LineBreak(),
        CheckBox("favorite", False), "Mark as favorite", LineBreak(),
        Button("Save", save_recipe),
        Button("Back", index),
    ])


@route
def save_recipe(state: State, name: str, category: str, servings: str, cost: str,
                ingredients: str, instructions: str, protein: str, carbs: str,
                fat: str, favorite: bool) -> Page:
    macros = [to_float(protein), to_float(carbs), to_float(fat)]
    servings_number = to_float(servings)
    cost_number = to_float(cost)

    # Input validation (if statements)
    if name.strip() == "":
        state.message = "Please enter a recipe name."
        return add_recipe(state)
    for recipe in state.recipes:
        if recipe.name.lower() == name.strip().lower():
            state.message = "A recipe with that name already exists."
            return add_recipe(state)
    if servings_number < 1:
        state.message = "Servings must be a whole number greater than zero."
        return add_recipe(state)
    if cost_number < 0:
        state.message = "Cost must be a number that is not negative."
        return add_recipe(state)
    if min(macros) < 0:
        state.message = "Macros must be numbers that are not negative."
        return add_recipe(state)

    state.recipes.append(Recipe(name.strip(), category, int(servings_number), ingredients,
                                instructions, cost_number, macros, favorite))
    state.message = "Recipe successfully added!"
    return index(state)


# ---------------------------------------------------------------- view
@route
def view_recipe(state: State, chosen_name: str) -> Page:
    # Find the chosen recipe's position in the full list
    for position in range(len(state.recipes)):
        if state.recipes[position].name == chosen_name:
            state.selected = position
    return recipe_page(state)


@route
def recipe_page(state: State) -> Page:
    if not (0 <= state.selected < len(state.recipes)):
        state.message = "Please select a valid recipe."
        return index(state)

    recipe = state.recipes[state.selected]
    protein, carbs, fat = recipe.macros
    star = "★ Favorite Recipe" if recipe.favorite else "☆ Not a Favorite"
    protein_note = "High Protein Recipe" if protein >= HIGH_PROTEIN_GRAMS else "Regular Protein Recipe"
    fav_button = "Remove Favorite" if recipe.favorite else "Add Favorite"

    return Page(state, [
        Header(recipe.name, 1),
        star, LineBreak(),
        f"Category: {recipe.category}  |  Servings: {recipe.servings}  |  Cost: ${recipe.cost:.2f}",
        Header("Ingredients", 2), recipe.ingredients,
        Header("Instructions", 2), recipe.instructions,
        Header("Macros", 2),
        f"Protein: {protein}g  |  Carbs: {carbs}g  |  Fat: {fat}g",
        LineBreak(), protein_note, LineBreak(),
        Button(fav_button, toggle_favorite),
        Button("Delete", delete_recipe),
        Button("Back", index),
    ])


@route
def toggle_favorite(state: State) -> Page:
    if 0 <= state.selected < len(state.recipes):
        recipe = state.recipes[state.selected]
        recipe.favorite = not recipe.favorite
    return recipe_page(state)


@route
def delete_recipe(state: State) -> Page:
    if 0 <= state.selected < len(state.recipes):
        state.recipes.pop(state.selected)
        state.selected = -1
        state.message = "Recipe deleted!"
    else:
        state.message = "Please select a valid recipe."
    return index(state)


# ---------------------------------------------------------------- filter
@route
def filter_page(state: State) -> Page:
    return Page(state, [
        Header("Filter Recipes", 1),
        "Filter by:", LineBreak(),
        "Category:", SelectBox("category", FILTER_CATEGORIES, state.category_filter), LineBreak(),
        CheckBox("favorites", state.favorites_only), "Favorites only", LineBreak(),
        Button("Apply", apply_filter),
        Button("Cancel", index),
    ])


@route
def apply_filter(state: State, category: str, favorites: bool) -> Page:
    state.category_filter = category
    state.favorites_only = favorites
    state.message = f"Filter applied: {len(matching_recipes(state))} recipe(s) match."
    return index(state)


# ---------------------------------------------------------------- stats
@route
def stats_page(state: State) -> Page:
    favorite_count = 0
    highest_protein = -1.0
    highest_protein_name = "None yet"
    category_counts = {}
    for category in CATEGORIES:
        category_counts[category] = 0

    for recipe in state.recipes:
        if recipe.favorite:
            favorite_count += 1
        if recipe.macros[0] > highest_protein:
            highest_protein = recipe.macros[0]
            highest_protein_name = f"{recipe.name} ({recipe.macros[0]}g)"
        category_counts[recipe.category] += 1

    content = [
        Header("Stats", 1),
        f"Recipe count: {len(state.recipes)}", LineBreak(),
        f"Favorites: {favorite_count}", LineBreak(),
        f"Highest protein: {highest_protein_name}", LineBreak(),
        Header("Recipes per category", 2),
    ]
    for category in CATEGORIES:
        content.append(f"{category}: {category_counts[category]}")
        content.append(LineBreak())
    content.append(Button("Back", index))
    return Page(state, content)


start_server(State([], "", -1, "All", False))
