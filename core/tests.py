import os
from django.test import TestCase
from cryptography.fernet import Fernet
import importlib

# The 'encryption' module is imported to be tested.
from core import encryption

class EncryptionServiceTests(TestCase):

    def setUp(self):
        """Set up a clean environment for each test."""
        # Store the original key to restore it later
        self.original_key = os.environ.get("APP_MASTER_KEY")

        # Generate a valid Fernet key for use in tests
        self.test_key = Fernet.generate_key().decode()
        os.environ["APP_MASTER_KEY"] = self.test_key

        # Reload the encryption module to ensure it picks up the new environment variable.
        # This is crucial because the module caches the Fernet instance.
        importlib.reload(encryption)

    def tearDown(self):
        """Restore the environment after each test."""
        if self.original_key is None:
            # If there was no key initially, remove the one we set.
            if "APP_MASTER_KEY" in os.environ:
                del os.environ["APP_MASTER_KEY"]
        else:
            # Otherwise, restore the original key.
            os.environ["APP_MASTER_KEY"] = self.original_key

        # Reload the module again to clean up the state for the next test class.
        importlib.reload(encryption)

    def test_encrypt_decrypt_successful_cycle(self):
        """Tests that data can be encrypted and successfully decrypted back to the original value."""
        original_text = "my-secret-api-key-12345"

        encrypted_text = encryption.encrypt(original_text)
        self.assertIsInstance(encrypted_text, str)
        self.assertNotEqual(original_text, encrypted_text)

        decrypted_text = encryption.decrypt(encrypted_text)
        self.assertEqual(original_text, decrypted_text)

    def test_decrypting_tampered_data_raises_value_error(self):
        """Tests that attempting to decrypt altered data raises a ValueError."""
        encrypted_text = encryption.encrypt("some data")
        # Introduce a change to the encrypted payload
        tampered_text = encrypted_text[:-1] + 'Z'

        with self.assertRaisesRegex(ValueError, "Cannot decrypt data: The token is invalid or has been tampered with."):
            encryption.decrypt(tampered_text)

    def test_encrypt_decrypt_without_master_key_raises_error(self):
        """Tests that the service fails if APP_MASTER_KEY is not set."""
        del os.environ["APP_MASTER_KEY"]
        importlib.reload(encryption)  # Force re-initialization

        with self.assertRaisesRegex(ValueError, "APP_MASTER_KEY environment variable not set"):
            encryption.encrypt("this will fail")

        with self.assertRaisesRegex(ValueError, "APP_MASTER_KEY environment variable not set"):
            # Provide some valid-looking encrypted data to test decryption path
            encrypted_data = "gAAAAABm_..."
            encryption.decrypt(encrypted_data)

    def test_invalid_master_key_raises_error(self):
        """Tests that using a malformed master key raises a ValueError."""
        os.environ["APP_MASTER_KEY"] = "this-is-not-a-base64-key"
        importlib.reload(encryption)  # Force re-initialization

        with self.assertRaisesRegex(ValueError, "Invalid APP_MASTER_KEY"):
            encryption.encrypt("this will also fail")

    def test_encrypting_non_string_input_raises_type_error(self):
        """Tests that the encrypt function rejects non-string input."""
        with self.assertRaises(TypeError):
            encryption.encrypt(12345)
        with self.assertRaises(TypeError):
            encryption.encrypt(b"some bytes")
        with self.assertRaises(TypeError):
            encryption.encrypt(None)

    def test_decrypting_non_string_input_raises_type_error(self):
        """Tests that the decrypt function rejects non-string input."""
        with self.assertRaises(TypeError):
            encryption.decrypt(12345)
        with self.assertRaises(TypeError):
            encryption.decrypt(b"some bytes")
        with self.assertRaises(TypeError):
            encryption.decrypt(None)
