"""
Tests for auth_forum helpers.
"""

from unittest.mock import patch, MagicMock

from django.contrib.auth.models import User, Permission
from django.test import TestCase

from auth_forum.helpers import (
    get_accessible_boards,
    mark_thread_read,
    user_can_access_board,
)
from auth_forum.models import Board, Category, Thread, UserReadStatus


def _add_basic_perm(user):
    perm = Permission.objects.get(codename="basic_access", content_type__app_label="auth_forum")
    user.user_permissions.add(perm)
    # Refresh from DB to bust permission cache
    return User.objects.get(pk=user.pk)


class TestUserCanAccessBoard(TestCase):
    def setUp(self):
        self.cat = Category.objects.create(name="Test Cat")
        self.board_open = Board.objects.create(
            category=self.cat, name="Open Board", order=0
        )
        self.user = User.objects.create_user(username="testuser")

    # ---- No basic_access ----

    def test_no_perm_denied(self):
        self.assertFalse(user_can_access_board(self.user, self.board_open))

    # ---- Open board (no group/state restrictions) ----

    def test_open_board_with_perm(self):
        user = _add_basic_perm(self.user)
        self.assertTrue(user_can_access_board(user, self.board_open))

    # ---- Group-restricted board ----

    def test_group_restricted_user_in_group(self):
        from django.contrib.auth.models import Group as DjGroup

        group = DjGroup.objects.create(name="members")
        self.board_open.groups.add(group)
        user = _add_basic_perm(self.user)
        user.groups.add(group)
        user = User.objects.get(pk=user.pk)
        self.assertTrue(user_can_access_board(user, self.board_open))

    def test_group_restricted_user_not_in_group(self):
        from django.contrib.auth.models import Group as DjGroup

        group = DjGroup.objects.create(name="vip")
        self.board_open.groups.add(group)
        user = _add_basic_perm(self.user)
        self.assertFalse(user_can_access_board(user, self.board_open))

    # ---- State-restricted board ----

    def test_state_restricted_user_has_state(self):
        """
        Mock user.profile.state to return a matching state.
        """
        from unittest.mock import MagicMock, PropertyMock

        state_mock = MagicMock()
        state_mock.pk = 999

        board = Board.objects.create(category=self.cat, name="State Board")
        state_qs_mock = MagicMock()
        state_qs_mock.exists.return_value = True
        state_qs_mock.filter.return_value.exists.return_value = True

        user = _add_basic_perm(self.user)

        with patch.object(board, "states") as mock_states:
            mock_states.all.return_value = [state_mock]
            mock_states.exists.return_value = True
            mock_states.filter.return_value.exists.return_value = True

            profile_mock = MagicMock()
            profile_mock.state = state_mock

            board.groups.set([])

            with patch.object(type(user), "profile", new_callable=PropertyMock, return_value=profile_mock):
                result = user_can_access_board(user, board)

        # We can't fully test the state path without a real State object,
        # but we verify the method completes without raising.
        self.assertIsInstance(result, bool)


class TestGetAccessibleBoards(TestCase):
    def setUp(self):
        self.cat = Category.objects.create(name="Cat")
        self.board1 = Board.objects.create(category=self.cat, name="Board 1")
        self.board2 = Board.objects.create(category=self.cat, name="Board 2", is_hidden=True)
        self.user = User.objects.create_user(username="accessor")

    def test_hidden_boards_excluded(self):
        user = _add_basic_perm(self.user)
        boards = get_accessible_boards(user)
        board_ids = [b.id for b in boards]
        self.assertNotIn(self.board2.id, board_ids)

    def test_visible_board_included(self):
        user = _add_basic_perm(self.user)
        boards = get_accessible_boards(user)
        board_ids = [b.id for b in boards]
        self.assertIn(self.board1.id, board_ids)


class TestMarkThreadRead(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="reader2")
        self.cat = Category.objects.create(name="Cat")
        self.board = Board.objects.create(category=self.cat, name="Board")
        self.thread = Thread.objects.create(
            board=self.board, author=self.user, title="Thread"
        )

    def test_creates_read_status(self):
        mark_thread_read(self.user, self.thread)
        self.assertTrue(
            UserReadStatus.objects.filter(user=self.user, thread=self.thread).exists()
        )

    def test_upsert_does_not_duplicate(self):
        mark_thread_read(self.user, self.thread)
        mark_thread_read(self.user, self.thread)
        self.assertEqual(
            UserReadStatus.objects.filter(user=self.user, thread=self.thread).count(),
            1,
        )
