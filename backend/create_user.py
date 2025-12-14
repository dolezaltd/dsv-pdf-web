#!/usr/bin/env python3
"""
Skript pro vytvoření/aktualizaci uživatelských přihlašovacích údajů.

Použití:
    python3 create_user.py

Skript se zeptá na uživatelské jméno a heslo, vygeneruje bcrypt hash
a uloží údaje do users.json.
"""
import json
import getpass
from pathlib import Path

try:
    import bcrypt
except ImportError:
    print("Chyba: Modul 'bcrypt' není nainstalován.")
    print("Nainstalujte ho pomocí: pip install bcrypt")
    exit(1)


def hash_password(password: str) -> str:
    """Vytvoří bcrypt hash z hesla."""
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def save_user(username: str, password_hash: str, users_file: Path):
    """Uloží uživatele do JSON souboru."""
    data = {
        "username": username,
        "password_hash": password_hash
    }
    with open(users_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Uživatel '{username}' byl úspěšně uložen do {users_file}")


def main():
    users_file = Path(__file__).parent / "users.json"
    
    print("=" * 50)
    print("Vytvoření/aktualizace přihlašovacích údajů")
    print("=" * 50)
    print()
    
    # Načtení existujícího uživatele (pokud existuje)
    existing_username = None
    if users_file.exists():
        try:
            with open(users_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                existing_username = data.get('username')
                print(f"Existující uživatel: {existing_username}")
        except (json.JSONDecodeError, KeyError):
            pass
    
    # Zadání uživatelského jména
    if existing_username:
        username = input(f"Uživatelské jméno [{existing_username}]: ").strip()
        if not username:
            username = existing_username
    else:
        username = input("Uživatelské jméno: ").strip()
        while not username:
            print("Uživatelské jméno nesmí být prázdné.")
            username = input("Uživatelské jméno: ").strip()
    
    # Zadání hesla
    print()
    password = getpass.getpass("Nové heslo: ")
    while len(password) < 4:
        print("Heslo musí mít alespoň 4 znaky.")
        password = getpass.getpass("Nové heslo: ")
    
    password_confirm = getpass.getpass("Potvrzení hesla: ")
    while password != password_confirm:
        print("Hesla se neshodují. Zkuste to znovu.")
        password = getpass.getpass("Nové heslo: ")
        password_confirm = getpass.getpass("Potvrzení hesla: ")
    
    # Vytvoření hashe a uložení
    print()
    print("Generuji hash hesla...")
    password_hash = hash_password(password)
    save_user(username, password_hash, users_file)
    
    print()
    print("Hotovo! Můžete se nyní přihlásit s novými údaji.")


if __name__ == "__main__":
    main()
