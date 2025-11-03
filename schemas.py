"""
Database Schemas

Define your MongoDB collection schemas here using Pydantic models.
These schemas are used for data validation in your application.

Each Pydantic model represents a collection in your database.
Model name is converted to lowercase for the collection name:
- User -> "user" collection
- Product -> "product" collection
- BlogPost -> "blogs" collection
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Literal

# Example schemas (keep for reference)
class User(BaseModel):
    """
    Users collection schema
    Collection name: "user" (lowercase of class name)
    """
    name: str = Field(..., description="Full name")
    email: str = Field(..., description="Email address")
    address: str = Field(..., description="Address")
    age: Optional[int] = Field(None, ge=0, le=120, description="Age in years")
    is_active: bool = Field(True, description="Whether user is active")

class Product(BaseModel):
    """
    Products collection schema
    Collection name: "product" (lowercase of class name)
    """
    title: str = Field(..., description="Product title")
    description: Optional[str] = Field(None, description="Product description")
    price: float = Field(..., ge=0, description="Price in dollars")
    category: str = Field(..., description="Product category")
    in_stock: bool = Field(True, description="Whether product is in stock")

# ClipMaster schemas
class Clip(BaseModel):
    caption: Optional[str] = None
    duration: Optional[float] = None
    aspect_ratio: Optional[str] = None
    thumbnail_url: Optional[str] = None
    download_url: Optional[str] = None

class Job(BaseModel):
    status: Literal['queued', 'processing', 'completed', 'failed'] = 'queued'
    progress: int = 0
    message: Optional[str] = None

    # Source information
    source_type: Literal['file', 'links']
    original_filename: Optional[str] = None
    sources: Optional[List[str]] = None

    # Options
    clip_length: Optional[str] = 'auto'
    aspect_ratio: Optional[str] = 'auto'
    auto_highlights: bool = True

    # Results
    clips: Optional[List[Clip]] = None
    error: Optional[str] = None
