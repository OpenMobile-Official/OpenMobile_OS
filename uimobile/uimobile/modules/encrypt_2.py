# encryption.py
from cryptography.fernet import Fernet
import os
import json

KEY_PATH = os.path.join("config", "key.key")

def load_key() -> bytes:
    """
    Loads the encryption key from file or generates one if not found.
    """
    os.makedirs(os.path.dirname(KEY_PATH), exist_ok=True)

    if not os.path.exists(KEY_PATH):
        key = Fernet.generate_key()
        with open(KEY_PATH, "wb") as f:
            f.write(key)
    else:
        with open(KEY_PATH, "rb") as f:
            key = f.read()

    return key

def get_fernet() -> Fernet:
    """
    Returns a Fernet object for encryption/decryption.
    """
    key = load_key()
    return Fernet(key)

def encrypt_user_data(user_data: dict, filepath: str):
    """
    Encrypts a user data dictionary and writes it to a file.
    """
    fernet = get_fernet()
    json_str = json.dumps(user_data)
    encrypted = fernet.encrypt(json_str.encode("utf-8"))
    
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "wb") as f:
        f.write(encrypted)

def decrypt_user_data(filepath: str) -> dict:
    """
    Decrypts encrypted user data from a file and returns the original dictionary.
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Encrypted user file not found: {filepath}")

    fernet = get_fernet()
    with open(filepath, "rb") as f:
        encrypted = f.read()

    try:
        decrypted_json_str = fernet.decrypt(encrypted).decode("utf-8")
        return json.loads(decrypted_json_str)
    except Exception as e:
        raise ValueError(f"Failed to decrypt or parse user data: {e}")
