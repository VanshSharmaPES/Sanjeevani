import unittest
from unittest.mock import patch, MagicMock
from db import get_db_status

class SQLiGuardTests(unittest.TestCase):
    @patch('db._get_conn')
    def test_get_db_status_whitelists_tables(self, mock_get_conn):
        # Setup mock connection and cursor
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        
        # Mock fetchall for table names query to return allowed tables + a malicious table
        mock_cursor.fetchall.side_effect = [
            [("users",), ("medicines",), ("malicious_table; DROP TABLE users;",)], # first call to fetch table list
            (10,), # count for users table
            (100,) # count for medicines table
        ]
        
        # Run function
        status = get_db_status()
        
        # Verify row counts contains only whitelisted tables
        self.assertIn("users", status["row_counts"])
        self.assertIn("medicines", status["row_counts"])
        self.assertNotIn("malicious_table; DROP TABLE users;", status["row_counts"])
        
        # Verify execute was called with SELECT COUNT(*) only for whitelisted tables
        calls = [call[0][0] for call in mock_cursor.execute.call_args_list]
        self.assertIn("SELECT COUNT(*) FROM [users]", calls)
        self.assertIn("SELECT COUNT(*) FROM [medicines]", calls)
        self.assertNotIn("SELECT COUNT(*) FROM [malicious_table; DROP TABLE users;]", calls)

if __name__ == "__main__":
    unittest.main()
