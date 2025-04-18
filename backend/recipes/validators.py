import re

from django.conf import settings
from django.core.exceptions import ValidationError


USERNAME_PATTERN = re.compile(r'[^\w.@+-]+')


def validate_username(username: str) -> None:
    """
    Валидатор имени пользователя.

    - Запрещает использовать имя, совпадающее с USER_PROFILE_URL.
    - Проверяет наличие недопустимых символов (вне диапазона \w, ., @, +, -).
    """
    _validate_reserved_username(username)
    _validate_username_characters(username)


def _validate_reserved_username(username: str) -> None:
    """Проверяет, не зарезервировано ли имя пользователя."""
    if username == settings.USER_PROFILE_URL:
        raise ValidationError(
            f"Использовать имя '{settings.USER_PROFILE_URL}' в качестве username запрещено!"
        )


def _validate_username_characters(username: str) -> None:
    """Проверяет имя на наличие недопустимых символов."""
    invalid_chars = USERNAME_PATTERN.findall(username)
    if invalid_chars:
        raise ValidationError(
            f"Поле 'username' содержит недопустимые символы: {set(invalid_chars)}"
        )
