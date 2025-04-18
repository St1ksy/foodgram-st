from django.core.exceptions import ValidationError
from django.shortcuts import redirect


from .models import Recipe


def recipe_detail(request, pk):
    """
    Перенаправляет пользователя на страницу рецепта по заданному идентификатору.
    
    Если рецепт не найден — возбуждается ValidationError.
    """
    if not Recipe.objects.filter(pk=pk).exists():
        raise ValidationError(f'Рецепт с id {pk} отсутствует.')

    return redirect(f'/recipes/{pk}/')
