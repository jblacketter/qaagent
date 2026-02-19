"""Tests for branch store — test_run_promote functionality."""

from unittest.mock import patch, MagicMock

from qaagent.branch import store as branch_store


class TestTestRunPromote:
    """Tests for the test_run_promote store function."""

    def test_promote_existing_run(self):
        """Promoting an existing run sets promoted_to_regression = 1."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.rowcount = 1
        mock_conn.execute.return_value = mock_cursor

        with patch.object(branch_store, "db") as mock_db:
            mock_db.get_db.return_value = mock_conn
            result = branch_store.test_run_promote(42)

        assert result is True
        mock_conn.execute.assert_called_once_with(
            "UPDATE branch_test_runs SET promoted_to_regression = 1 WHERE id = ?",
            (42,),
        )
        mock_conn.commit.assert_called_once()

    def test_promote_nonexistent_run(self):
        """Promoting a nonexistent run returns False."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.rowcount = 0
        mock_conn.execute.return_value = mock_cursor

        with patch.object(branch_store, "db") as mock_db:
            mock_db.get_db.return_value = mock_conn
            result = branch_store.test_run_promote(999)

        assert result is False
