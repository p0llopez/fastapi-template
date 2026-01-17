from sqlalchemy import Column, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()

Base.metadata.naming_convention = {
    "idx": "ix_%(column_0_label)s",  # Index
    "uq": "uq_%(table_name)s_%(column_0_name)s",  # Unique constraint
    "ck": "ck_%(table_name)s_%(constraint_name)s",  # Check constraint
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",  # Foreign key
    "pk": "pk_%(table_name)s",  # Primary key
}


class SQLAlchemyBaseModel(Base):
    __abstract__ = True

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Timestamp when the record was created",
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="Timestamp when the record was last updated",
    )
