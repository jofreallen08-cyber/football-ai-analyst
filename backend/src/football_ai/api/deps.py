"""Common FastAPI dependencies."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Query
from sqlalchemy.orm import Session

from football_ai.core.db import get_session

SessionDep = Annotated[Session, Depends(get_session)]
Limit = Annotated[int, Query(ge=1, le=200, description="Numero massimo di elementi")]
Offset = Annotated[int, Query(ge=0, le=100_000, description="Elementi da saltare")]
SearchQuery = Annotated[str | None, Query(min_length=1, max_length=100)]
