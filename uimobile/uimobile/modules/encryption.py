from cryptography.fernet import Fernet
import os

KEY_PATH = os.path.join("config", "key.key")

def load_key():
    if not os.path.exists(KEY_PATH):
        os.makedirs(os.path.dirname(KEY_PATH), exist_ok=True)
        key = Fernet.generate_key()
        with open(KEY_PATH, "wb") as f:
            f.write(key)
    else:
        with open(KEY_PATH, "rb") as f:
            key = f.read()
    return key

def encrypt_string(string: str) -> bytes:
    fernet = Fernet(load_key())
    return fernet.encrypt(string.encode())

def decrypt_string(encrypted: bytes) -> str:
    fernet = Fernet(load_key())
    return fernet.decrypt(encrypted).decode()
def decrypt_user_data(filepath):
    # Your decryption code here
    # Example dummy:
    import json
    with open(filepath, 'rb') as f:
        encrypted = f.read()
    # Decrypt here...
    decrypted_json = b'{"username": "admin", "password": "pass123"}'  # Replace with actual decrypt output
    return json.loads(decrypted_json)
