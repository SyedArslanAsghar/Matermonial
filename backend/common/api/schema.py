"""Shared OpenAPI building blocks (KI-40): the pagination envelope and query parameters,
matching ``StandardPagination`` (count / next / previous / results; doc 04 §16)."""

from drf_spectacular.utils import OpenApiParameter
from rest_framework import serializers

PAGE_PARAMETERS = [
    OpenApiParameter("page", int, OpenApiParameter.QUERY, required=False),
    OpenApiParameter("page_size", int, OpenApiParameter.QUERY, required=False),
]


def paginated(name: str, item: type[serializers.Serializer]) -> type[serializers.Serializer]:
    return type(
        name,
        (serializers.Serializer,),
        {
            "count": serializers.IntegerField(),
            "next": serializers.URLField(allow_null=True),
            "previous": serializers.URLField(allow_null=True),
            "results": item(many=True),
        },
    )


class DetailSerializer(serializers.Serializer):
    detail = serializers.CharField()
