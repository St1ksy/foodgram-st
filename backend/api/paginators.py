from rest_framework.pagination import PageNumberPagination


class PaginatorWithLimit(PageNumberPagination):
    """
    Пагинатор, позволяющий задать лимит количества элементов на странице.
    """

    page_size_query_param = 'limit'
    page_size = 6
