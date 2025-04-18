from datetime import datetime


def generate_txt(ingredients, recipes):
    """
    Создаёт текстовое представление списка покупок и рецептов
    на основе переданных данных.
    """

    current_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
    header = f'Список покупок от {current_timestamp}\n'

    recipe_lines = ['Рецепты:']
    for index, recipe_name in enumerate(recipes, start=1):
        recipe_lines.append(f'{index}. {recipe_name}')

    ingredient_header = '\nПродукты:'
    ingredient_lines = []
    for index, ingredient in enumerate(ingredients, start=1):
        name = ingredient.get('name', '').capitalize()
        amount = ingredient.get('amount', 0)
        unit = ingredient.get('measurement', '')
        ingredient_lines.append(f'{index}. {name}: {amount} {unit}')

    full_text = '\n'.join([header] + recipe_lines + [ingredient_header] + ingredient_lines)
    return full_text
