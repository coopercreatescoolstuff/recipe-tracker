from drafter import *
from dataclasses import dataclass
from bakery import assert_equal

# Constants (allowed: no global variables, but constants are fine)
CATEGORIES = ["Breakfast", "Lunch", "Dinner", "Dessert", "Snack"]
FILTER_CATEGORIES = ["All"] + CATEGORIES
HIGH_PROTEIN_GRAMS = 30.0

"""
Recipe data class, has all the information a recipe would need
"""
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

"""
Keeps information that the app needs between pages, basically the memory
"""
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
    """
    Builds the home page with the recipes that match the current filter, if any
    """
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
    """
    Builds the page where the user enters a recipes information
    """
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
    """
    Checks if the submitted feilds and save a recipe when all values are true and valid
    """
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
    """
    Finds a recipe by its selected name, opens its detail page
    """
    # Find the chosen recipe's position in the full list
    for position in range(len(state.recipes)):
        if state.recipes[position].name == chosen_name:
            state.selected = position
    return recipe_page(state)


@route
def recipe_page(state: State) -> Page:
    """
    Builds a page with all the information of the selected recipe
    """
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
    """
    Reverse the current setting for the favorite of the current recipe
    """
    if 0 <= state.selected < len(state.recipes):
        recipe = state.recipes[state.selected]
        recipe.favorite = not recipe.favorite
    return recipe_page(state)


@route
def delete_recipe(state: State) -> Page:
    """
    Deletes a selected recipe from the saved list
    """
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
    """
    Builds the page where the user choose recipe-list filters
    """
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
    """
    Updates the active filters and return to the home page
    """
    state.category_filter = category
    state.favorites_only = favorites
    state.message = f"Filter applied: {len(matching_recipes(state))} recipe(s) match."
    return index(state)


# ---------------------------------------------------------------- stats
@route
def stats_page(state: State) -> Page:
    """
    Calculates the totals and builds a page summarizing the saved recipes
    """
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

# ---------------------------------------------------------------- unit tests
# These tests use Bakery's assert_equal function to check important behavior.
# There are only two or three tests for each function that performs logic.

# Test converting text into numbers, including invalid input.
assert_equal(to_float("12.5"), 12.5)
assert_equal(to_float(" 3 "), 3.0)
assert_equal(to_float("not a number"), -1.0)

# Test filtering by category and by favorite status.
test_breakfast = Recipe("Pancakes", "Breakfast", 2, "Flour", "Mix", 4.0,
                        [8.0, 30.0, 5.0], True)
test_dinner = Recipe("Pasta", "Dinner", 3, "Pasta", "Boil", 6.0,
                     [12.0, 45.0, 9.0], False)
test_state = State([test_breakfast, test_dinner], "", -1, "All", False)
assert_equal(matching_recipes(test_state), [test_breakfast, test_dinner])
test_state.category_filter = "Breakfast"
assert_equal(matching_recipes(test_state), [test_breakfast])
test_state.category_filter = "All"
test_state.favorites_only = True
assert_equal(matching_recipes(test_state), [test_breakfast])

# Test saving a valid recipe and rejecting invalid or duplicate names.
test_add_state = State([], "", -1, "All", False)
save_recipe(test_add_state, "Pancakes", "Breakfast", "2", "4.50",
            "Flour, milk, eggs", "Mix and cook", "8", "30", "5", True)
assert_equal(len(test_add_state.recipes), 1)
assert_equal(test_add_state.recipes[0].name, "Pancakes")
test_empty_state = State([], "", -1, "All", False)
save_recipe(test_empty_state, "   ", "Breakfast", "2", "4.50",
            "Flour", "Mix", "8", "30", "5", False)
assert_equal(test_empty_state.message, "Please enter a recipe name.")
test_duplicate_state = State([test_breakfast], "", -1, "All", False)
save_recipe(test_duplicate_state, "pAnCaKeS", "Breakfast", "2", "4.50",
            "Flour", "Mix", "8", "30", "5", False)
assert_equal(len(test_duplicate_state.recipes), 1)

# Test selecting an existing recipe and handling a name that is not found.
test_view_state = State([test_breakfast, test_dinner], "", -1, "All", False)
view_recipe(test_view_state, "Pasta")
assert_equal(test_view_state.selected, 1)
test_missing_view_state = State([test_breakfast], "", -1, "All", False)
view_recipe(test_missing_view_state, "Pizza")
assert_equal(test_missing_view_state.message, "Please select a valid recipe.")

# Test switching a recipe's favorite status on and off.
test_favorite_state = State([test_breakfast], "", 0, "All", False)
toggle_favorite(test_favorite_state)
assert_equal(test_favorite_state.recipes[0].favorite, False)
toggle_favorite(test_favorite_state)
assert_equal(test_favorite_state.recipes[0].favorite, True)

# Test deleting a selected recipe and handling an invalid selection.
test_delete_state = State([test_breakfast], "", 0, "All", False)
delete_recipe(test_delete_state)
assert_equal(len(test_delete_state.recipes), 0)
assert_equal(test_delete_state.message, "Recipe deleted!")
test_invalid_delete_state = State([test_breakfast], "", 5, "All", False)
delete_recipe(test_invalid_delete_state)
assert_equal(len(test_invalid_delete_state.recipes), 1)

# Test applying category and favorites filters.
test_filter_state = State([test_breakfast, test_dinner], "", -1, "All", False)
apply_filter(test_filter_state, "Dessert", True)
assert_equal(test_filter_state.category_filter, "Dessert")
assert_equal(test_filter_state.favorites_only, True)

# Test that the statistics page does not change the saved recipes.
test_stats_state = State([test_breakfast, test_dinner], "", -1, "All", False)
stats_page(test_stats_state)
assert_equal(len(test_stats_state.recipes), 2)
assert_equal(test_stats_state.recipes[0], test_breakfast)


# Start the web application after the unit tests have completed.
start_server(State([], "", -1, "All", False))
