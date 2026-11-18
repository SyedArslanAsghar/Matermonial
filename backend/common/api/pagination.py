"""Standard pagination (doc 04 §16): count / next / previous / results.

Default and maximum page sizes come from settings (REST_FRAMEWORK["PAGE_SIZE"],
API_MAX_PAGE_SIZE).
"""

from django.conf import settings
from rest_framework.pagination import PageNumberPagination


class StandardPagination(PageNumberPagination):
    page_size_query_param = "page_size"

    @property
    def max_page_size(self) -> int:
        return settings.API_MAX_PAGE_SIZE
