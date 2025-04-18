from django.urls import reverse
from django.db.models import F, Sum
from django.http import FileResponse
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from djoser.serializers import SetPasswordSerializer
from rest_framework.exceptions import ValidationError
from rest_framework import permissions, status, viewsets
from djoser.views import UserViewSet as DjoserUserViewSet
from django_filters.rest_framework import DjangoFilterBackend

from .utils import generate_txt
from .constants import TXT_FILENAME
from .permissions import ReadOnlyOrAuthor
from .paginators import PaginatorWithLimit
from recipes.models import (
    User,
    Recipe,
    Favorite,
    Ingredient,
    ShoppingCart,
    Subscriptions,
)

from .serializers import (
    AvatarSerializer,
    IngredientSerializer,
    PublicUserSerializer,
    UserCreationSerializer,
    RecipeSummarySerializer,
    RecipeRetrieveSerializer,
    RecipeCreateUpdateSerializer,
    SubscriptionDetailSerializer,
)


class UserViewSet(DjoserUserViewSet):
    """ViewSet для управления пользователями."""

    pagination_class = PaginatorWithLimit

    def get_serializer_class(self):
        if self.action == "set_password":
            return SetPasswordSerializer
        if self.request.method == "GET":
            return PublicUserSerializer
        return UserCreationSerializer

    def get_permissions(self):
        if self.action == "me":
            return [permissions.IsAuthenticated()]
        if self.action in ("list", "retrieve"):
            return [permissions.AllowAny()]
        return super().get_permissions()

    @action(
        detail=False,
        methods=["put", "delete"],
        permission_classes=[permissions.IsAuthenticated],
        url_path="me/avatar",
    )
    def avatar(self, request):
        """Обновляет или удаляет аватар текущего пользователя."""
        if request.method == "PUT":
            serializer = AvatarSerializer(request.user, data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)
        request.user.avatar = None
        request.user.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        permission_classes=[permissions.IsAuthenticated],
        url_path="subscriptions",
    )
    def subscriptions(self, request):
        """
        Возвращает список пользователей, на которых подписан пользователь.
        """
        subscriptions = User.objects.filter(authors__user=request.user)
        page = self.paginate_queryset(subscriptions)
        if page is not None:
            serializer = SubscriptionDetailSerializer(
                page, many=True, context={"request": request}
            )
            return self.get_paginated_response(serializer.data)

        serializer = SubscriptionDetailSerializer(
            subscriptions, many=True, context={"request": request}
        )
        return Response(serializer.data)

    @action(
        detail=True,
        methods=["post", "delete"],
        url_path="subscribe",
        permission_classes=[permissions.IsAuthenticated],
    )
    def subscribe(self, request, id=None):
        """Подписка и отписка текущего пользователя от другого пользователя."""
        author = get_object_or_404(User, pk=id)
        user = request.user

        if user == author:
            raise ValidationError("Нельзя подписаться на самого себя.")
        
        if request.method == "POST":
            _, created = Subscriptions.objects.get_or_create(user=user, author=author)
            if not created:
                raise ValidationError("Вы уже подписаны на этого пользователя!")
            return Response(
                SubscriptionDetailSerializer(author, context={"request": request}).data,
                status=status.HTTP_201_CREATED,
            )
        
        subscription = Subscriptions.objects.filter(user=user, author=author)
        if not subscription.exists():
            return Response(
                {"errors": "Вы не подписаны на этого пользователя."},
                status=status.HTTP_400_BAD_REQUEST
            )
        subscription.delete()
        
        return Response(status=status.HTTP_204_NO_CONTENT)


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet для управления ингридиентами."""

    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    filter_backends = (DjangoFilterBackend,)
    permission_classes = [permissions.AllowAny]

class RecipeViewSet(viewsets.ModelViewSet):
    """ViewSet для управления рецептами."""

    queryset = Recipe.objects.all().order_by("-pub_date")
    filter_backends = (DjangoFilterBackend,)
    pagination_class = PaginatorWithLimit
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, ReadOnlyOrAuthor]

    def get_serializer_class(self):
        """Возвращает соответствующий сериализатор для получения и создания."""
        if self.action in ["retrieve", "get_link"]:
            return RecipeRetrieveSerializer
        return RecipeCreateUpdateSerializer

    @action(detail=True, permission_classes=[permissions.AllowAny], url_path="get-link")
    def get_link(self, request, pk=None):
        """Получение короткой ссылки."""
        recipe = get_object_or_404(Recipe, pk=pk)
        return Response(
            {
                "short-link": request.build_absolute_uri(
                    reverse("recipes:shortlink", args=[recipe.pk])
                )
            },
            status=status.HTTP_200_OK,
        )

    @action(
        detail=False,
        methods=["get"],
        permission_classes=[permissions.IsAuthenticated],
        url_path="download_shopping_cart",
    )
    def download_shopping_cart(self, request):
        """Возвращает список покупок в формате TXT."""

        user = request.user
        ingredients = (
            Ingredient.objects.filter(
                recipeingredients__recipe__shoppingcarts__user=user
            )
            .values("name", measurement=F("measurement_unit"))
            .annotate(amount=Sum("recipeingredients__amount"))
        )
        return FileResponse(
            generate_txt(ingredients, Recipe.objects.filter(shoppingcarts__user=user)),
            content_type="text/plain",
            filename=TXT_FILENAME,
        )

    @staticmethod
    def shoppingcart_favorite_method(request, pk, model, delete_message):
        recipe = get_object_or_404(Recipe, pk=pk)

        if request.method == "POST":
            _, created = model.objects.get_or_create(user=request.user, recipe=recipe)
            if created:
                return Response(
                    RecipeSummarySerializer(recipe).data, 
                    status=status.HTTP_201_CREATED
                )
            raise ValidationError("Этот рецепт уже в списке.")
        
        relation = model.objects.filter(user=request.user, recipe=recipe)
        if not relation.exists():
            return Response(
                {"errors": "Этого рецепта нет в списке."},
                status=status.HTTP_400_BAD_REQUEST
            )
    
        relation.delete()
        return Response(
            {"delete": delete_message},
            status=status.HTTP_204_NO_CONTENT
        )

    @action(
        detail=True,
        url_path="favorite",
        methods=("post", "delete"),
        permission_classes=(permissions.IsAuthenticated,),
    )
    def favorite(self, request, pk=None):
        """Добавляет рецепт в избранное или удаляет его из избранного."""
        return self.shoppingcart_favorite_method(
            request, pk, Favorite, delete_message="Рецепт удален из избранного"
        )

    @action(
        detail=True,
        url_path="shopping_cart",
        methods=("post", "delete"),
        permission_classes=(permissions.IsAuthenticated,),
    )
    def shopping_cart(self, request, pk=None):
        """Добавляет рецепт в список покупок или удаляет его."""
        return self.shoppingcart_favorite_method(
            request, pk, ShoppingCart, delete_message="Рецепт удален из списка покупок"
        )
