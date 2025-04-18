from rest_framework import serializers
from drf_extra_fields.fields import Base64ImageField
from djoser.serializers import (
    UserCreateSerializer as DjoserUserCreateSerializer,
    UserSerializer as DjoserUserSerializer
)

from recipes.constants import MIN_INGREDIENT_AMOUNT
from recipes.models import (
    User,
    Recipe,
    Ingredient,
    Subscriptions,
    RecipeIngredient,
)

class UserCreationSerializer(DjoserUserCreateSerializer):
    """Сериализатор для регистрации нового пользователя."""

    email = serializers.EmailField()

    class Meta(DjoserUserCreateSerializer.Meta):
        fields = (
            *DjoserUserCreateSerializer.Meta.fields,
        )


class AvatarSerializer(serializers.ModelSerializer):
    """Сериализатор для аватара."""

    avatar = Base64ImageField()

    class Meta:
        model = User
        fields = ('avatar',)



class PublicUserSerializer(DjoserUserSerializer):
    """
    Расширенный сериализатор пользователя:
    добавляет информацию о подписке на пользователя.
    """

    is_subscribed = serializers.SerializerMethodField()

    class Meta(DjoserUserSerializer.Meta):
        fields = (
            'is_subscribed',
            'avatar',
            *DjoserUserSerializer.Meta.fields,
        )

    def get_is_subscribed(self, target_user):
        """
        Проверяет, подписан ли текущий пользователь на `target_user`.
        """
        request = self.context.get('request')
        current_user = request.user if request else None

        if not (current_user and current_user.is_authenticated):
            return False

        return Subscriptions.objects.filter(
            user=current_user,
            author=target_user
        ).exists()


class SubscriptionDetailSerializer(PublicUserSerializer):
    """
    Сериализатор для отображения подписок:
    включает рецепты автора и их количество.
    """

    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.IntegerField(
        source='recipes.count',
        read_only=True
    )

    class Meta(PublicUserSerializer.Meta):
        model = User
        fields = (
            *PublicUserSerializer.Meta.fields,
            'recipes',
            'recipes_count',
        )

    def get_recipes(self, subscribed_author):
        """
        Возвращает рецепты автора, ограниченные параметром `recipes_limit` в GET-запросе.
        """
        request = self.context.get('request')
        default_limit = 10**10

        try:
            limit = int(request.GET.get('recipes_limit', default_limit))
        except (ValueError, AttributeError):
            limit = default_limit

        author_recipes = subscribed_author.recipes.all()[:limit]

        return RecipeSummarySerializer(
            author_recipes,
            many=True,
            context=self.context
        ).data


class IngredientSerializer(serializers.ModelSerializer):
    """Сериализатор для отображения информации об ингредиенте."""

    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')
        

class RecipeSummarySerializer(serializers.ModelSerializer):
    """Сериализатор для модели Recipe для списка подписок."""

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class RecipeIngredientDetailSerializer(serializers.ModelSerializer):
    """
    Сериализатор для детального отображения ингредиентов,
    связанных с рецептом. Извлекает информацию через связанную модель.
    """

    id = serializers.PrimaryKeyRelatedField(
        source='ingredient', 
        read_only=True
    )
    name = serializers.SlugRelatedField(
        source='ingredient',
        read_only=True,
        slug_field='name'
    )
    measurement_unit = serializers.SlugRelatedField(
        source='ingredient',
        read_only=True,
        slug_field='measurement_unit'
    )

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'name', 'measurement_unit', 'amount')


class RecipeIngredientCreateUpdateSerializer(serializers.ModelSerializer):
    """
    Сериализатор для добавления ингредиентов к рецепту:
    включает количество и ссылку на объект ингредиента.
    """

    id = serializers.PrimaryKeyRelatedField(
        queryset=Ingredient.objects.all()
    )
    amount = serializers.IntegerField()

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'amount')

    def validate_amount(self, input_amount):
        """
        Проверяет, что введённое количество ингредиента
        не меньше заданного минимального значения.
        """
        if input_amount < MIN_INGREDIENT_AMOUNT:
            raise serializers.ValidationError(
                f'Указано недопустимо малое количество: {input_amount}. '
                f'Минимум: {MIN_INGREDIENT_AMOUNT}.'
            )
        return input_amount


class RecipeRetrieveSerializer(serializers.ModelSerializer):
    """
    Сериализатор для детального представления рецепта.
    """

    author = PublicUserSerializer(read_only=True)
    ingredients = RecipeIngredientDetailSerializer(
        source='recipeingredients',
        many=True
    )
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = (
            'id',
            'name',
            'ingredients',
            'text',
            'image',
            'cooking_time',
            'author',
            'is_favorited',
            'is_in_shopping_cart',
        )
        read_only_fields = fields

    def get_is_favorited(self, recipe_instance):
        """
        Возвращает True, если рецепт добавлен в избранное текущим пользователем.
        """
        request = self.context.get('request')
        user = getattr(request, 'user', None)

        if not user or not user.is_authenticated:
            return False

        is_favorited = recipe_instance.favorites.filter(user=user).exists()
        return is_favorited

    def get_is_in_shopping_cart(self, recipe_instance):
        """
        Возвращает True, если рецепт находится в списке покупок пользователя.
        """
        request = self.context.get('request')
        user = getattr(request, 'user', None)

        if not user or not user.is_authenticated:
            return False

        is_in_cart = recipe_instance.shoppingcarts.filter(user=user).exists()
        return is_in_cart


class RecipeCreateUpdateSerializer(serializers.ModelSerializer):
    """
    Сериализатор для добавления и обновления рецепта с использованием id.
    """

    ingredients = RecipeIngredientCreateUpdateSerializer(many=True)
    image = Base64ImageField(required=True)

    class Meta:
        model = Recipe
        fields = (
            'name',
            'ingredients',
            'text',
            'image',
            'cooking_time',
            'id',
        )
        read_only_fields = ('author',)

    def to_representation(self, instance):
        """
        Преобразует данные экземпляра рецепта в формат для GET-запроса.
        """
        return RecipeRetrieveSerializer(instance, context=self.context).data

    def validate_image(self, value):
        """
        Проверяет, что изображение загружено и не пустое.
        """
        if not value:
            raise serializers.ValidationError(
                'Поле изображения не может быть пустым. Загрузите файл.'
            )
        return value

    @staticmethod
    def validate_items(items, model, field_name):
        """
        Проверяет, что элементы с указанными id существуют и уникальны.
        """
        if not items:
            raise serializers.ValidationError(
                {field_name: f'Поле {field_name} не может быть пустым.'}
            )

        existing_items = model.objects.filter(id__in=items).values_list('id', flat=True)
        missing_items = set(items) - set(existing_items)
        if missing_items:
            raise serializers.ValidationError(
                {field_name: f'Элемент(ы) с id {missing_items} не существуют!'}
            )

        non_unique_ids = set(item for item in items if items.count(item) > 1)
        if non_unique_ids:
            raise serializers.ValidationError(
                {field_name: f'Элементы с id {non_unique_ids} не уникальны!'}
            )

    def validate(self, data):
        """
        Проверка на корректность ингредиентов.
        """
        ingredients = self.initial_data.get('ingredients')

        if not ingredients:
            raise serializers.ValidationError(
                'Поле "ingredients" не может быть пустым.'
            )

        ingredient_ids = [ingredient['id'] for ingredient in ingredients]
        self.validate_items(
            ingredient_ids,
            model=Ingredient,
            field_name='ingredients',
        )

        return data

    def set_ingredients(self, recipe, ingredients):
        """
        Добавляет ингредиенты в промежуточную модель для рецепта.
        """
        recipe_ingredients = [
            RecipeIngredient(
                ingredient=ingredient['id'],
                amount=ingredient['amount'],
                recipe=recipe,
            )
            for ingredient in ingredients
        ]
        RecipeIngredient.objects.bulk_create(recipe_ingredients)

    def create(self, validated_data):
        """
        Создаёт новый рецепт с привязанными ингредиентами.
        """
        ingredients = validated_data.pop('ingredients')
        author = self.context.get('request').user

        recipe_instance = Recipe.objects.create(author=author, **validated_data)
        self.set_ingredients(recipe_instance, ingredients)
        return recipe_instance

    def update(self, instance, validated_data):
        """
        Обновляет существующий рецепт, включая ингредиенты.
        """
        ingredients_data = validated_data.pop('ingredients')

        instance.save()
        instance.ingredients.clear()

        self.set_ingredients(instance, ingredients_data)
        
        return super().update(instance, validated_data)
