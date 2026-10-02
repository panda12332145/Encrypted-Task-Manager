#!/usr/bin/env python3
"""Ponto de entrada do Encrypted-Task-Manager.

Uso:
  python main.py
"""
import getpass
import sys

from src.tui import run


def main():
    try:
        password = getpass.getpass("🔑 Senha mestra: ")
    except Exception:
        password = input("🔑 Senha mestra: ")
    if not password:
        print("❌ Senha vazia.")
        sys.exit(1)
    run(password)


if __name__ == "__main__":
    main()
