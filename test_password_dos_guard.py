import unittest
import time
from db import register_user, authenticate_user, reset_password

class PasswordDoSGuardTests(unittest.TestCase):
    def test_register_user_rejects_long_password(self):
        long_pass = "P" * 100000
        success, message = register_user("testdosuser", long_pass, "patient")
        self.assertFalse(success)
        self.assertEqual(message, "Password cannot be more than 128 characters")

    def test_authenticate_user_rejects_long_password(self):
        long_pass = "P" * 100000
        # Should return immediately and not block for hashing
        start = time.time()
        success, user_id, role = authenticate_user("hemanth", long_pass)
        duration = time.time() - start
        self.assertFalse(success)
        self.assertIsNone(user_id)
        # Should be extremely fast as it rejects before hashing
        self.assertLess(duration, 0.05, f"Authentication took too long: {duration:.4f}s")

    def test_reset_password_rejects_long_password(self):
        long_pass = "P" * 100000
        success, message = reset_password("hemanth", long_pass)
        self.assertFalse(success)
        self.assertEqual(message, "Password cannot be more than 128 characters.")

if __name__ == "__main__":
    unittest.main()
