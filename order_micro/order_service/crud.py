from sqlalchemy.orm import Session
from typing import List, Optional
from order_service.models import Order, OrderItem, OrderStatus
from order_service.schemas import OrderCreate, OrderUpdate

class OrderCRUD:
    @staticmethod
    def create_order(db: Session, user_id: int, cart_id: int, items: List[dict], shipping_address: Optional[str] = None) -> Order:
        """Create a new order with items"""
        total_amount = sum(item['price'] * item['quantity'] for item in items)
        
        order = Order(
            user_id=user_id,
            cart_id=cart_id,
            total_amount=total_amount,
            shipping_address=shipping_address,
            status=OrderStatus.PENDING
        )
        db.add(order)
        db.flush()  # Get order.id
        
        # Create order items
        for item in items:
            order_item = OrderItem(
                order_id=order.id,
                product_id=item['product_id'],
                product_name=item['product_name'],
                quantity=item['quantity'],
                price=item['price']
            )
            db.add(order_item)
        
        db.commit()
        db.refresh(order)
        return order
    
    @staticmethod
    def get_order_by_id(db: Session, order_id: int) -> Optional[Order]:
        """Get order by ID"""
        return db.query(Order).filter(Order.id == order_id).first()
    
    @staticmethod
    def get_orders_by_user(db: Session, user_id: int, skip: int = 0, limit: int = 100) -> List[Order]:
        """Get all orders for a user"""
        return db.query(Order).filter(Order.user_id == user_id).offset(skip).limit(limit).all()
    
    @staticmethod
    def get_all_orders(db: Session, skip: int = 0, limit: int = 100) -> List[Order]:
        """Get all orders"""
        return db.query(Order).offset(skip).limit(limit).all()
    
    @staticmethod
    def update_order(db: Session, order_id: int, order_update: OrderUpdate) -> Optional[Order]:
        """Update order"""
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            return None
        
        update_data = order_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(order, field, value)
        
        db.commit()
        db.refresh(order)
        return order
    
    @staticmethod
    def cancel_order(db: Session, order_id: int) -> bool:
        """Cancel an order"""
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order or order.status in [OrderStatus.SHIPPED, OrderStatus.DELIVERED, OrderStatus.CANCELLED]:
            return False
        
        order.status = OrderStatus.CANCELLED
        db.commit()
        return True