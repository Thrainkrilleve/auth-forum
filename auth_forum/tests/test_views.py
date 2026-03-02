"""
Tests for auth_forum views.
"""

from django.contrib.auth.models import Permission, User
from django.test import TestCase
from django.urls import reverse

from auth_forum.models import Board, Category, Post, Thread


def _add_perm(user, codename):
    perm = Permission.objects.get(
        codename=codename, content_type__app_label="auth_forum"
    )
    user.user_permissions.add(perm)
    return User.objects.get(pk=user.pk)


def _make_user(username="testuser"):
    return User.objects.create_user(username=username, password="password")


def _make_board(name="Test Board"):
    cat = Category.objects.get_or_create(name="General")[0]
    return Board.objects.create(category=cat, name=name)


def _make_thread(board, user, title="Test Thread"):
    t = Thread.objects.create(board=board, author=user, title=title)
    Post.objects.create(thread=t, author=user, content="First post", is_first_post=True)
    return t


class TestIndexView(TestCase):
    def setUp(self):
        self.user = _make_user("idx_user")
        self.url = reverse("auth_forum:index")

    def test_requires_login(self):
        response = self.client.get(self.url)
        self.assertRedirects(response, f"/accounts/login/?next={self.url}", fetch_redirect_response=False)

    def test_requires_basic_access(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

    def test_index_ok_with_perm(self):
        user = _add_perm(self.user, "basic_access")
        self.client.force_login(user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Forum")


class TestBoardView(TestCase):
    def setUp(self):
        self.user = _make_user("board_user")
        self.board = _make_board("Board View Test")
        self.url = reverse("auth_forum:board", kwargs={"board_slug": self.board.slug})

    def test_requires_basic_access(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

    def test_board_view_ok(self):
        user = _add_perm(self.user, "basic_access")
        self.client.force_login(user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Board View Test")

    def test_restricted_board_denied(self):
        from django.contrib.auth.models import Group as DjGroup

        vip_group = DjGroup.objects.create(name="vip_board_test")
        self.board.groups.add(vip_group)

        user = _add_perm(self.user, "basic_access")
        self.client.force_login(user)
        response = self.client.get(self.url, follow=True)
        # Should redirect back to index with error
        self.assertRedirects(response, reverse("auth_forum:index"))


class TestThreadView(TestCase):
    def setUp(self):
        self.user = _make_user("thread_view_user")
        self.board = _make_board("Thread View Board")
        self.thread = _make_thread(self.board, self.user, "Thread View Test")
        self.url = reverse("auth_forum:thread", kwargs={"thread_pk": self.thread.pk})

    def test_requires_basic_access(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

    def test_thread_view_ok(self):
        user = _add_perm(self.user, "basic_access")
        self.client.force_login(user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Thread View Test")

    def test_locked_thread_hides_reply_form(self):
        self.thread.is_locked = True
        self.thread.save()

        user = _add_perm(self.user, "basic_access")
        self.client.force_login(user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Post a Reply")
        self.assertContains(response, "locked")

    def test_locked_thread_reply_blocked(self):
        self.thread.is_locked = True
        self.thread.save()

        user = _add_perm(self.user, "basic_access")
        self.client.force_login(user)
        response = self.client.post(
            self.url,
            {"content": "Trying to reply to locked thread"},
            follow=True,
        )
        self.assertRedirects(response, self.url)
        self.assertEqual(self.thread.posts.count(), 1)  # no new post

    def test_reply_creates_post(self):
        user = _add_perm(self.user, "basic_access")
        self.client.force_login(user)

        with self.settings(CELERY_TASK_ALWAYS_EAGER=True):
            response = self.client.post(
                self.url,
                {"content": "A valid reply"},
                follow=True,
            )
        self.assertRedirects(response, self.url)
        self.assertEqual(self.thread.posts.count(), 2)


class TestNewThreadView(TestCase):
    def setUp(self):
        self.user = _make_user("new_thread_user")
        self.board = _make_board("New Thread Board")
        self.url = reverse(
            "auth_forum:new_thread", kwargs={"board_slug": self.board.slug}
        )

    def test_get_form(self):
        user = _add_perm(self.user, "basic_access")
        self.client.force_login(user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_create_thread(self):
        user = _add_perm(self.user, "basic_access")
        self.client.force_login(user)
        response = self.client.post(
            self.url,
            {"title": "A Brand New Thread", "content": "Opening post content"},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Thread.objects.filter(title="A Brand New Thread").exists())

    def test_empty_title_rejected(self):
        user = _add_perm(self.user, "basic_access")
        self.client.force_login(user)
        response = self.client.post(
            self.url,
            {"title": "", "content": "Content without title"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Thread.objects.filter(board=self.board).exists())


class TestEditPostView(TestCase):
    def setUp(self):
        self.author = _make_user("edit_author")
        self.other = _make_user("edit_other")
        self.board = _make_board("Edit Board")
        self.thread = _make_thread(self.board, self.author, "Edit Thread")
        self.post = self.thread.posts.first()

    def test_author_can_edit(self):
        user = _add_perm(self.author, "basic_access")
        self.client.force_login(user)
        url = reverse("auth_forum:edit_post", kwargs={"post_pk": self.post.pk})
        response = self.client.post(url, {"content": "Updated content"}, follow=True)
        self.post.refresh_from_db()
        self.assertEqual(self.post.content, "Updated content")

    def test_non_author_denied(self):
        user = _add_perm(self.other, "basic_access")
        self.client.force_login(user)
        url = reverse("auth_forum:edit_post", kwargs={"post_pk": self.post.pk})
        response = self.client.post(url, {"content": "Hacked"}, follow=True)
        self.post.refresh_from_db()
        self.assertNotEqual(self.post.content, "Hacked")


class TestSearchView(TestCase):
    def setUp(self):
        self.user = _make_user("search_user")

    def test_search_requires_perm(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("auth_forum:search"))
        self.assertEqual(response.status_code, 302)

    def test_search_ok(self):
        user = _add_perm(self.user, "basic_access")
        self.client.force_login(user)
        response = self.client.get(reverse("auth_forum:search"), {"q": "hello"})
        self.assertEqual(response.status_code, 200)
