import os
from cryptography.fernet import Fernet, InvalidToken

# This is a module-level cache for the Fernet instance.
# It's initialized on the first encryption/decryption call.
_fernet_instance = None

def _get_fernet():
    """
    Initializes and returns a singleton Fernet instance.
    Raises ValueError if the master key is missing or invalid.
    """
    global _fernet_instance
    if _fernet_instance is None:
        master_key = os.getenv("APP_MASTER_KEY")
        if not master_key:
            # This is a critical configuration error. The application cannot
            # proceed securely without it. Failing fast is the best approach.
            raise ValueError("APP_MASTER_KEY environment variable not set. Cannot perform encryption/decryption.")

        try:
            key = master_key.encode()
            _fernet_instance = Fernet(key)
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid APP_MASTER_KEY. It must be a 32-byte URL-safe base64-encoded key. Details: {e}")

    return _fernet_instance

def encrypt(data: str) -> str:
    """Encrypts a string and returns the URL-safe, base64-encoded encrypted string."""
    if not isinstance(data, str):
        raise TypeError("Data to encrypt must be a string.")

    fernet = _get_fernet()
    return fernet.encrypt(data.encode()).decode()

def decrypt(encrypted_data: str) -> str:
    """Decrypts a string and returns the original string."""
    if not isinstance(encrypted_data, str):
        raise TypeError("Data to decrypt must be a string.")

    fernet = _get_fernet()
    try:
        return fernet.decrypt(encrypted_data.encode()).decode()
    except InvalidToken:
        # This error occurs if the token is invalid, expired, or tampered with.
        # This should be treated as a potential security event.
        # TODO: Add logging here for security auditing purposes.
        raise ValueError("Cannot decrypt data: The token is invalid or has been tampered with.")
