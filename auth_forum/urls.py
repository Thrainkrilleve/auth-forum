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
    # Category management
    path("manage/category/new/", views.create_category, name="create_category"),
    path("manage/category/<int:category_pk>/edit/", views.edit_category, name="edit_category"),
    path("manage/category/<int:category_pk>/delete/", views.delete_category, name="delete_category"),
    # Board management
    path("manage/board/new/", views.create_board, name="create_board"),
    path("manage/board/new/<int:category_pk>/", views.create_board, name="create_board_in_category"),
    path("manage/board/<slug:board_slug>/edit/", views.edit_board, name="edit_board"),
    path("manage/board/<slug:board_slug>/delete/", views.delete_board, name="delete_board"),
    # Reactions, subscriptions, polls
    path("post/<int:post_pk>/react/", views.toggle_reaction, name="toggle_reaction"),
    path("thread/<int:thread_pk>/subscribe/", views.toggle_subscription, name="toggle_subscription"),
    path("poll/<int:poll_pk>/vote/", views.vote_poll, name="vote_poll"),
]
