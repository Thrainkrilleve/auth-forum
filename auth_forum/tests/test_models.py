"""
Tests for auth_forum models.
"""

from django.contrib.auth.models import User
from django.test import TestCase

from auth_forum.models import Board, Category, General, Post, Thread, UserReadStatus


class TestGeneralModel(TestCase):
    def test_permissions_defined(self):
        perms = dict(General._meta.permissions)
        self.assertIn("basic_access", perms)
        self.assertIn("manage_forum", perms)

    def test_not_managed(self):
        self.assertFalse(General._meta.managed)


class TestCategoryModel(TestCase):
    def setUp(self):
        self.cat = Category.objects.create(name="Test Category", order=1)

    def test_str(self):
        self.assertEqual(str(self.cat), "Test Category")

    def test_ordering(self):
        cat2 = Category.objects.create(name="Another Category", order=0)
        cats = list(Category.objects.all())
        self.assertEqual(cats[0], cat2)  # order=0 comes first


class TestBoardModel(TestCase):
    def setUp(self):
        self.cat = Category.objects.create(name="General", order=0)
        self.board = Board.objects.create(
            category=self.cat, name="Announcements", order=0
        )

    def test_str(self):
        self.assertEqual(str(self.board), "General / Announcements")

    def test_slug_auto_generated(self):
        self.assertEqual(self.board.slug, "announcements")

    def test_slug_unique_collision(self):
        board2 = Board.objects.create(
            category=self.cat, name="Announcements", order=1
        )
        self.assertNotEqual(self.board.slug, board2.slug)
        self.assertTrue(board2.slug.startswith("announcements"))

    def test_thread_count(self):
        user = User.objects.create_user(username="tester")
        Thread.objects.create(board=self.board, author=user, title="Hello")
        self.assertEqual(self.board.thread_count, 1)


class TestThreadModel(TestCase):
    def setUp(self):
        self.cat = Category.objects.create(name="Cat")
        self.board = Board.objects.create(category=self.cat, name="Board")
        self.user = User.objects.create_user(username="thread_author")
        self.thread = Thread.objects.create(
            board=self.board, author=self.user, title="My Test Thread"
        )

    def test_str(self):
        self.assertEqual(str(self.thread), "My Test Thread")

    def test_slug_auto_generated(self):
        self.assertIn("my-test-thread", self.thread.slug)

    def test_is_locked_default_false(self):
        self.assertFalse(self.thread.is_locked)

    def test_is_pinned_default_false(self):
        self.assertFalse(self.thread.is_pinned)

    def test_post_count(self):
        Post.objects.create(
            thread=self.thread, author=self.user, content="Hello", is_first_post=True
        )
        self.assertEqual(self.thread.post_count, 1)


class TestPostModel(TestCase):
    def setUp(self):
        self.cat = Category.objects.create(name="Cat")
        self.board = Board.objects.create(category=self.cat, name="Board")
        self.user = User.objects.create_user(username="poster")
        self.thread = Thread.objects.create(
            board=self.board, author=self.user, title="Thread"
        )

    def test_str(self):
        post = Post.objects.create(
            thread=self.thread, author=self.user, content="Test content"
        )
        self.assertIn("poster", str(post))
        self.assertIn("Thread", str(post))

    def test_str_deleted_author(self):
        post = Post.objects.create(
            thread=self.thread, author=None, content="Orphan post"
        )
        self.assertIn("deleted", str(post))

    def test_ordering_chronological(self):
        p1 = Post.objects.create(
            thread=self.thread, author=self.user, content="First"
        )
        p2 = Post.objects.create(
            thread=self.thread, author=self.user, content="Second"
        )
        posts = list(self.thread.posts.all())
        self.assertEqual(posts[0], p1)
        self.assertEqual(posts[1], p2)


class TestUserReadStatus(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="reader")
        self.cat = Category.objects.create(name="Cat")
        self.board = Board.objects.create(category=self.cat, name="Board")
        self.thread = Thread.objects.create(
            board=self.board, author=self.user, title="A Thread"
        )

    def test_str(self):
        status = UserReadStatus.objects.create(user=self.user, thread=self.thread)
        self.assertIn("reader", str(status))
        self.assertIn("A Thread", str(status))

    def test_unique_together(self):
        UserReadStatus.objects.create(user=self.user, thread=self.thread)
        with self.assertRaises(Exception):
            UserReadStatus.objects.create(user=self.user, thread=self.thread)
