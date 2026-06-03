# app/schemas.py
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

# ── Request schemas (what client sends) ───────────────
class PostCreate(BaseModel):
    title:   str = Field(..., min_length=3, max_length=200)
    content: str = Field(..., min_length=10)
    author:  str = Field(..., min_length=2, max_length=100)

class PostUpdate(BaseModel):
    title:     Optional[str] = Field(None, min_length=3, max_length=200)
    content:   Optional[str] = Field(None, min_length=10)
    published: Optional[bool] = None

# ── Response schemas (what server returns) ────────────
class PostResponse(BaseModel):
    id:         int
    title:      str
    content:    str
    author:     str
    published:  bool
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True  # allows ORM model → Pydantic

class PostListResponse(BaseModel):
    total: int
    posts: list[PostResponse]