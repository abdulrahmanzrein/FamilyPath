# shared parent class for all our DB tables (Provider, Search, SearchResult)
# every model inherits from this so SQLAlchemy knows about them all in one place

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
