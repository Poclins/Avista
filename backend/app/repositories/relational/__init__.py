"""Repositorio relacional (Capa 3): interfaz y adaptador SQLAlchemy."""

from app.repositories.relational.base import RelationalRepo
from app.repositories.relational.sqlalchemy_repo import SqlAlchemyRelationalRepo

__all__ = ["RelationalRepo", "SqlAlchemyRelationalRepo"]
