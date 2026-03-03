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
    path("post/<int:post_pk>/history/", views.post_history, name="post_history"),
    path("thread/<int:thread_pk>/lock/", views.lock_thread, name="lock_thread"),
    path("thread/<int:thread_pk>/pin/", views.pin_thread, name="pin_thread"),
    path("thread/<int:thread_pk>/move/", views.move_thread, name="move_thread"),
    path("thread/<int:thread_pk>/first-unread/", views.thread_first_unread, name="thread_first_unread"),
    path("search/", views.search, name="search"),
    path("stats/", views.stats, name="stats"),
    # Mark as read
    path("mark-all-read/", views.mark_all_read, name="mark_all_read"),
    path("board/<slug:board_slug>/mark-read/", views.mark_board_read, name="mark_board_read"),
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
    path("board/<slug:board_slug>/subscribe/", views.toggle_board_subscription, name="toggle_board_subscription"),
    path("poll/<int:poll_pk>/vote/", views.vote_poll, name="vote_poll"),
    # JSON APIs
    path("api/preview/", views.preview_content, name="preview_content"),
    path("api/mention-autocomplete/", views.mention_autocomplete, name="mention_autocomplete"),
    path("api/upload-image/", views.upload_image, name="upload_image"),
]
