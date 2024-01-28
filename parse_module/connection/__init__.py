from .database import ParsingDB

DEBUG_DB = False
db_manager = ParsingDB()

__all__ = ['db_manager']
