from rest_framework import permissions


class ReadOnlyOrAuthor(permissions.BasePermission):
    """
    Пользовательское разрешение: 
    - Разрешает безопасные методы (GET, HEAD, OPTIONS) всем.
    - Разрешает изменение и удаление только автору объекта.
    """

    def has_object_permission(self, request, view, obj):
        is_safe_method = request.method in permissions.SAFE_METHODS
        is_author = obj.author == request.user
        return is_safe_method or is_author