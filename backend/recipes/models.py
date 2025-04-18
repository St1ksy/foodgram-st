from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator
from django.utils.translation import gettext_lazy as _

from .validators import validate_username
from .constants import (
    MIN_COOKING_TIME, MIN_INGREDIENT_AMOUNT,
    MAX_LENGTH_USERNAME, MAX_LENGTH_FIRST_NAME,
    MAX_LENGTH_LAST_NAME, MAX_LENGTH_EMAIL_ADDRESS,
    MAX_LENGTH_UNIT, MAX_LENGTH_NAME, MAX_LENGTH_TEXT,
)


class User(AbstractUser):
    """Модель пользователя."""

    username = models.CharField(
        verbose_name='Имя пользователя',
        max_length=MAX_LENGTH_USERNAME,
        validators=[validate_username],
        unique=True,    
    )
    first_name = models.CharField(
        verbose_name='Имя',
        max_length=MAX_LENGTH_FIRST_NAME,
    )
    last_name = models.CharField(
        verbose_name='Фамилия',
        max_length=MAX_LENGTH_LAST_NAME,
    )
    email = models.EmailField(
        verbose_name='Электронная почта',
        max_length=MAX_LENGTH_EMAIL_ADDRESS,
        unique=True,
    )
    avatar = models.ImageField(
        null=True,
        default=None,
        upload_to='user_images',
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    class Meta:
        ordering = ('username',)
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self) -> str:
        return self.username
    

class Ingredient(models.Model):
    """Модель ингредиента и единицей измерения."""

    name = models.CharField(
        verbose_name='Название',
        max_length=MAX_LENGTH_NAME,
    )
    measurement_unit = models.CharField(
        verbose_name='Единица измерения',
        max_length=MAX_LENGTH_UNIT,
    )

    class Meta:
        ordering = ('name',)
        verbose_name = 'Продукт'
        verbose_name_plural = 'Продукты'
        constraints = (
            models.UniqueConstraint(
                fields=('name', 'measurement_unit',),
                name='unique_ingredient_name_unit',
            ),
        )

    def __str__(self) -> str:
        return f'{self.name} ({self.measurement_unit})'


class Recipe(models.Model):
    """Рецепт блюда с изображением и ингредиентами."""

    name = models.CharField(
        verbose_name='Название',
        max_length=MAX_LENGTH_NAME
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name='Автор',
        on_delete=models.CASCADE,
        null=True,
    )
    text = models.TextField(
        verbose_name='Описание',
        max_length=MAX_LENGTH_TEXT,
    )
    image = models.ImageField(
        verbose_name='Изображение',
        upload_to='recipe_images/',
    )
    cooking_time = models.IntegerField(
        validators=[MinValueValidator(MIN_COOKING_TIME)],
        verbose_name='Время приготовления',
    )
    pub_date = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата публикации',
    )
    ingredients = models.ManyToManyField(
        Ingredient,
        through='RecipeIngredient',
        verbose_name='Продукты',
    )


    class Meta:
        ordering = ('-pub_date',)
        default_related_name = '%(class)ss'
        verbose_name = 'Рецепт'
        verbose_name_plural = 'Рецепты'
        constraints = (
            models.UniqueConstraint(
                fields=('name', 'author',),
                name='unique_recipe_title_author',
            ),
        )

    def __str__(self) -> str:
        return self.name[:MAX_LENGTH_NAME]
    

class UserRecipeBase(models.Model):
    """Базовая модель для связи пользователя и рецепта."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name='Пользователь',
        on_delete=models.CASCADE,     
    )
    recipe = models.ForeignKey(
        Recipe,
        verbose_name='Рецепт',
        on_delete=models.CASCADE,
    )

    class Meta:
        default_related_name = '%(class)ss'
        abstract = True
        constraints = (
            models.UniqueConstraint(
                fields=('user', 'recipe',),
                name='%(class)s_unique_user_recipe'
            ),
        )

    def __str__(self) -> str:
        username = self.user.username
        recipe_name = self.recipe.name
        return f'{username} связывается с {recipe_name}'


class RecipeIngredient(models.Model):
    """Модель связи рецепта и ингредиента."""

    recipe = models.ForeignKey(
        Recipe,
        verbose_name='Рецепты',
        on_delete=models.CASCADE
    )
    ingredient = models.ForeignKey(
        Ingredient,
        verbose_name='Продукты',
        on_delete=models.CASCADE
    )
    amount = models.IntegerField(
        validators=[MinValueValidator(MIN_INGREDIENT_AMOUNT)],
        verbose_name='Количество',
    )

    class Meta:
        ordering = ('recipe',)
        default_related_name = '%(class)ss'
        verbose_name = 'Продукт'
        verbose_name_plural = 'Продукты'
        constraints = (
            models.UniqueConstraint(
                fields=('recipe', 'ingredient',),
                name='unique_recipe_ingredient',
            ),
        )

    def __str__(self) -> str:
        unit = self.ingredient.measurement_unit
        name = self.ingredient.name
        recipe = self.recipe.name
        return f'{self.amount} {unit} {_("из")} {name} {_("для")} {recipe}'
    

class Subscriptions(models.Model):
    """Модель подписки пользователя на других пользователей."""

    author = models.ForeignKey(
        User,
        verbose_name='Автор',
        related_name='authors',
        on_delete=models.CASCADE,
    )
    user = models.ForeignKey(
        User,
        verbose_name='Подписчики',
        related_name='followers',
        on_delete=models.CASCADE,
    )

    class Meta:
        verbose_name = 'Подписка'
        verbose_name_plural = 'Подписки'
        constraints = (
            models.UniqueConstraint(
                fields=('user', 'author',),
                name='unique_user_author_subscription'
            ),
        )

    def __str__(self) -> str:
        return '{} подписался на {}'.format(
            self.user.username[:MAX_LENGTH_NAME],
            self.author.username[:MAX_LENGTH_NAME]
        )


class ShoppingCart(UserRecipeBase):
    """Модель списка покупок."""

    class Meta(UserRecipeBase.Meta):
        verbose_name = _('Список покупок')
        verbose_name_plural = _('Списки покупок')

    def __str__(self) -> str:
        username = self.user.username
        recipe_name = self.recipe.name
        return f'{username} добавил в список покупок {recipe_name}'
    

class Favorite(UserRecipeBase):
    """Модель избранных рецептов."""

    class Meta(UserRecipeBase.Meta):
        verbose_name = _('Избранный рецепт')
        verbose_name_plural = _('Избранные рецепты')

    def __str__(self) -> str:
        username = self.user.username
        recipe_name = self.recipe.name
        return f'{username} добавил в избранное {recipe_name}'
