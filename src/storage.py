"""Armazenamento criptografado do Encrypted-Task-Manager.

Cada tarefa é um arquivo .taf cifrado (AES-256-CBC) com chave derivada da
senha mestra via Scrypt. O salt de cada tarefa fica no índice (tarefas.json),
que guarda apenas metadados — nunca o conteúdo em claro.
"""
import base64
import json
import os

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

# Diretório dos dados: sobrescrevível via variável de ambiente (útil em
# testes e em máquinas sem ~/Documents). Padrão: ~/Documents/Tarefas
ENV_DIR = "TAREFAS_DIR"


def task_dir() -> str:
    d = os.environ.get(ENV_DIR) or os.path.join(
        os.path.expanduser("~"), "Documents", "Tarefas")
    os.makedirs(d, exist_ok=True)
    return d


def index_path() -> str:
    return os.path.join(task_dir(), "tarefas.json")


def derive_key(password: str, salt: bytes) -> bytes:
    kdf = Scrypt(salt=salt, length=32, n=2 ** 14, r=8, p=1,
                 backend=default_backend())
    return kdf.derive(password.encode())


def encrypt(key: bytes, plaintext: str) -> str:
    iv = os.urandom(16)
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv),
                    backend=default_backend())
    enc = cipher.encryptor()
    padder = padding.PKCS7(128).padder()
    padded = padder.update(plaintext.encode()) + padder.finalize()
    ct = enc.update(padded) + enc.finalize()
    return base64.b64encode(iv + ct).decode()


def decrypt(key: bytes, ciphertext_b64: str) -> str:
    raw = base64.b64decode(ciphertext_b64)
    iv, data = raw[:16], raw[16:]
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv),
                    backend=default_backend())
    dec = cipher.decryptor()
    padded = dec.update(data) + dec.finalize()
    unpadder = padding.PKCS7(128).unpadder()
    return (unpadder.update(padded) + unpadder.finalize()).decode()


def load_index() -> list:
    path = index_path()
    if not os.path.exists(path):
        return []
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        # índice corrompido não derruba o programa
        return []


def save_index(data: list) -> None:
    """Escrita atômica (tmp + replace) para nunca corromper o índice."""
    path = index_path()
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    os.replace(tmp, path)
