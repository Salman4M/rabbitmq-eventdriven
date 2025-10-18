from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import List, Optional

class CartItemBase(BaseModel):
    product_id: int
    product_name: str
    quantity: int = Field(ge=1)
    price: float = Field(ge=0)

class CartItemCreate(CartItemBase):
    pass

class CartItemUpdate(BaseModel):
    quantity: Optional[int] = Field(None, ge=1)
    price: Optional[float] = Field(None, ge=0)

class CartItemResponse(CartItemBase):
    id: int
    shopcart_id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ShopcartBase(BaseModel):
    user_id: int
    username: str
    email: EmailStr

class ShopcartCreate(ShopcartBase):
    pass

class ShopcartResponse(ShopcartBase):
    id: int
    is_active: bool
    items: List[CartItemResponse] = []
    created_at: datetime
    updated_at: datetime
    total_items: int
    total_price: float
    
    class Config:
        from_attributes = True

class ShopcartSummary(BaseModel):
    id: int
    user_id: int
    username: str
    email: str
    total_items: int
    total_price: float
    is_active: bool
    
    class Config:
        from_attributes = True