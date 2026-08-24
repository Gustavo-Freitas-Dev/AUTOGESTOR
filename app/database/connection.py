"""Compatibilidade para importações antigas da conexão do banco."""

from app.database.db import DATABASE_URL, SessionLocal, engine

__all__ = ["DATABASE_URL", "SessionLocal", "engine"]
