"""Import every model here so Alembic and the app see all tables on Base.metadata."""

from app.db.models.api_key import ApiKey
from app.db.models.chunk import Chunk
from app.db.models.document import Document
from app.db.models.tenant import Tenant
from app.db.models.user import User

__all__ = ["ApiKey", "Chunk", "Document", "Tenant", "User"]
