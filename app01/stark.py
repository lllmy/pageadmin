from stark.service.sites import site,ModelStark
from django.utils.safestring import mark_safe
from app01.models import Book, Publish, Author, AuthorDetail
from django.shortcuts import HttpResponse, render, redirect


class BookConfig(ModelStark):

    list_display = ["title", "price", "publish", "authors"]
    list_display_links = ["title", "publish", "authors"]
    search_fields = ["title","price"]

    # 批量操作

    def patch_init(self, request, queryset):
        queryset.update(price=100)


    patch_init.desc = "价格初始化"

    actions = [patch_init]


site.register(Book, BookConfig)
site.register(Publish)
site.register(Author)