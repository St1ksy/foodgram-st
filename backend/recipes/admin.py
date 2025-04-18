from django.urls import reverse
from django.contrib import admin
from django.utils.html import format_html
from django.contrib.auth.models import Group
from django.utils.safestring import mark_safe
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import ( 
    User,
    Recipe,
    Favorite,
    Ingredient,
    ShoppingCart,
    Subscriptions,
    RecipeIngredient, 
)

admin.site.unregister(Group)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = (
        'username',
        'email',
        'first_name',
        'last_name',
        'recipe_count',
        'subscription_count',
        'follower_count',
        'avatar'
    )
    search_fields = ('email', 'username')

    @admin.display(description='Рецепты')
    def recipe_count(self, user):
        count = user.recipes.count()
        if count:
            base_url = reverse('admin:recipes_recipe_changelist')
            query_string = f'?author__id={user.id}'
            full_url = f'{base_url}{query_string}'
            formatted_link = format_html('<a href="{}">{}</a>', full_url, count)
            return formatted_link
        
        return count

    @admin.display(description='Подписки')
    def subscription_count(self, user):
        count = user.authors.count()
        if count:
            subscriptions_url = reverse('admin:recipes_subscriptions_changelist')
            formatted_link = format_html('<a href="{}">{}</a>', subscriptions_url, count)
            return formatted_link
        return count

    @admin.display(description='Подписчики')
    def follower_count(self, user):
        count = user.followers.count()
        if count:
            subscriptions_url = reverse('admin:recipes_subscriptions_changelist')
            formatted_link = format_html('<a href="{}">{}</a>', subscriptions_url, count)
            return formatted_link
        return count

    @admin.display(description='Аватар')
    @mark_safe
    def avatar_image(self, user):
        avatar_url = user.avatar.url
        image_html = '<img src="{}" width="50" height="50" />'.format(avatar_url)
        return image_html


@admin.register(Subscriptions)
class SubscriptionsAdmin(admin.ModelAdmin):
    list_display = ('user', 'author')
    search_fields = ('user__username', 'author__username')


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('name', 'measurement_unit', 'recipe_count')
    search_fields = ('name', 'measurement_unit')

    @admin.display(description='Число рецептов')
    def recipe_count(self, ingredient):
        recipes_usage = ingredient.recipeingredients.count()
        return recipes_usage


class RecipeIngredientInline(admin.TabularInline):
    model = RecipeIngredient
    extra = 1


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'author',
        'cooking_time',
        'display_ingredients',
        'display_image',
        'favorite_count'
    )
    search_fields = ('name', 'author__username')
    readonly_fields = ('favorite_count',)
    exclude = ('slug_for_short_url',)
    inlines = [RecipeIngredientInline]

    @admin.display(description='Продукты')
    @mark_safe
    def display_ingredients(self, recipe):
        ingredients_info = []
        for relation in recipe.recipeingredients.all():
            ingredient_name = relation.ingredient.name
            unit = relation.ingredient.measurement_unit
            amount = relation.amount
            ingredients_info.append(f'{ingredient_name} ({unit}) - {amount}')
        return '<br>'.join(ingredients_info)

    @admin.display(description='Изображение')
    @mark_safe
    def display_image(self, recipe):
        image_url = recipe.image.url
        image_html = '<img src="{}" style="max-height: 100px;">'.format(image_url)
        return image_html

    @admin.display(description='Избранное')
    def favorite_count(self, recipe):
        fav_total = recipe.favorites.count()
        return fav_total


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('user', 'recipe')
    search_fields = ('user__username', 'recipe__name')


@admin.register(ShoppingCart)
class ShoppingCartAdmin(admin.ModelAdmin):
    list_display = ('user', 'recipe')
