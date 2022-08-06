from django.core.paginator import Page, Paginator
from django.db.models import QuerySet
from django.http import HttpRequest

from django.conf import settings


def get_paginator(request: HttpRequest, posts: QuerySet) -> Page:
    """Возвращает Paginator."""
    paginator = Paginator(posts, settings.QTY_POSTS)
    page_number = request.GET.get('page')
    return paginator.get_page(page_number)
