"""Modul pro načítání API klíčů z bezpečného úložiště."""
import json
import os
from pathlib import Path
from typing import Optional


def get_api_key(key_name: str = "openai", fallback_env: bool = True) -> Optional[str]:
    """
    Načte API klíč z .env souboru nebo z environment proměnných.
    
    Args:
        key_name: Název klíče (např. "openai", "anthropic", "google")
        fallback_env: Pokud True, zkusí najít klíč v environment proměnných jako fallback
        
    Returns:
        API klíč jako string nebo None pokud není nalezen
    """
    # Hledání .env souboru v kořenové složce projektu
    current_path = Path(__file__).resolve().parent.parent
    env_path = current_path / ".env"
    
    # Pokus o načtení z .env souboru
    if env_path.exists():
        try:
            from dotenv import dotenv_values
            env_vars = dotenv_values(env_path)
            env_key_name = f"{key_name.upper()}_API_KEY"
            api_key = env_vars.get(env_key_name)
            if api_key:
                return api_key
        except Exception as e:
            print(f"Varování: Nepodařilo se načíst API klíč z .env: {e}")
    
    # Fallback na environment proměnné
    if fallback_env:
        env_key_name = f"{key_name.upper()}_API_KEY"
        env_key = os.getenv(env_key_name)
        if env_key:
            return env_key
        
        # Speciální případy pro různé API klíče
        if key_name == "openai":
            openai_key = os.getenv("OPENAI_API_KEY")
            if openai_key:
                return openai_key
        elif key_name == "google":
            google_key = os.getenv("GOOGLE_API_KEY")
            if google_key:
                return google_key
    
    return None


def get_all_api_keys() -> dict:
    """
    Načte všechny API klíče z .env souboru.
    
    Returns:
        Slovník s API klíči nebo prázdný slovník pokud soubor neexistuje
    """
    current_path = Path(__file__).resolve().parent.parent
    env_path = current_path / ".env"
    
    if env_path.exists():
        try:
            from dotenv import dotenv_values
            env_vars = dotenv_values(env_path)
            return {
                "openai": env_vars.get("OPENAI_API_KEY"),
                "anthropic": env_vars.get("ANTHROPIC_API_KEY"),
                "google": env_vars.get("GOOGLE_API_KEY")
            }
        except Exception as e:
            print(f"Varování: Nepodařilo se načíst API klíče z .env: {e}")
    
    return {}


def check_api_key(key_name: str = "openai") -> bool:
    """
    Zkontroluje, zda je API klíč k dispozici.
    
    Args:
        key_name: Název klíče k ověření
        
    Returns:
        True pokud je klíč k dispozici, False jinak
    """
    return get_api_key(key_name) is not None

