from django.urls import path

from . import views

app_name = "auth_forum"

urlpatterns = [
    path("", views.index, name="index"),
    path("board/<slug:board_slug>/", views.board, name="board"),
    path("board/<slug:board_slug>/new-thread/", views.new_thread, name="new_thread"),
    path("thread/<int:thread_pk>/", views.thread, name="thread"),
    path("post/<int:post_pk>/edit/", views.edit_post, name="edit_post"),
    path("post/<int:post_pk>/delete/", views.delete_post, name="delete_post"),
    path("thread/<int:thread_pk>/lock/", views.lock_thread, name="lock_thread"),
    path("thread/<int:thread_pk>/pin/", views.pin_thread, name="pin_thread"),
    path("search/", views.search, name="search"),
]
