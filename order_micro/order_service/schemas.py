from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional
from order_service.models import OrderStatus

class OrderItemBase(BaseModel):
    product_id: int
    product_name: str
    quantity: int = Field(ge=1)
    price: float = Field(ge=0)

class OrderItemResponse(OrderItemBase):
    id: int
    order_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class OrderCreate(BaseModel):
    user_id: int
    shipping_address: Optional[str] = None

class OrderUpdate(BaseModel):
    status: Optional[OrderStatus] = None
    shipping_address: Optional[str] = None

class OrderResponse(BaseModel):
    id: int
    user_id: int
    cart_id: int
    total_amount: float
    status: OrderStatus
    shipping_address: Optional[str]
    items: List[OrderItemResponse] = []
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class OrderSummary(BaseModel):
    id: int
    user_id: int
    total_amount: float
    status: OrderStatus
    item_count: int
    created_at: datetime
    
    class Config:
        from_attributes = True