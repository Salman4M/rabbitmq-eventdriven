from sqlalchemy.orm import Session
from typing import List, Optional
from cart_service.models import Shopcart, CartItem
from cart_service.schemas import ShopcartCreate, CartItemCreate, CartItemUpdate

class ShopcartCRUD:
    @staticmethod
    def create_shopcart(db: Session, shopcart: ShopcartCreate) -> Shopcart:
        db_shopcart = Shopcart(**shopcart.dict())
        db.add(db_shopcart)
        db.commit()
        db.refresh(db_shopcart)
        return db_shopcart
    
    @staticmethod
    def get_shopcart_by_id(db: Session, shopcart_id: int) -> Optional[Shopcart]:
        return db.query(Shopcart).filter(Shopcart.id == shopcart_id).first()
    
    @staticmethod
    def get_shopcart_by_user_id(db: Session, user_id: int) -> Optional[Shopcart]:
        return db.query(Shopcart).filter(Shopcart.user_id == user_id).first()
    
    @staticmethod
    def get_all_shopcarts(db: Session, skip: int = 0, limit: int = 100) -> List[Shopcart]:
        return db.query(Shopcart).offset(skip).limit(limit).all()
    
    @staticmethod
    def delete_shopcart(db: Session, shopcart_id: int) -> bool:
        shopcart = db.query(Shopcart).filter(Shopcart.id == shopcart_id).first()
        if shopcart:
            db.delete(shopcart)
            db.commit()
            return True
        return False
    
    @staticmethod
    def clear_shopcart(db: Session, shopcart_id: int) -> bool:
        shopcart = db.query(Shopcart).filter(Shopcart.id == shopcart_id).first()
        if shopcart:
            db.query(CartItem).filter(CartItem.shopcart_id == shopcart_id).delete()
            db.commit()
            return True
        return False


class CartItemCRUD:
    @staticmethod
    def add_item(db: Session, shopcart_id: int, item: CartItemCreate) -> CartItem:
        # Check if item already exists in cart
        existing_item = db.query(CartItem).filter(
            CartItem.shopcart_id == shopcart_id,
            CartItem.product_id == item.product_id
        ).first()
        
        if existing_item:
            # Update quantity
            existing_item.quantity += item.quantity
            db.commit()
            db.refresh(existing_item)
            return existing_item
        else:
            # Add new item
            db_item = CartItem(**item.dict(), shopcart_id=shopcart_id)
            db.add(db_item)
            db.commit()
            db.refresh(db_item)
            return db_item
    
    @staticmethod
    def get_item(db: Session, item_id: int) -> Optional[CartItem]:
        return db.query(CartItem).filter(CartItem.id == item_id).first()
    
    @staticmethod
    def update_item(db: Session, item_id: int, item_update: CartItemUpdate) -> Optional[CartItem]:
        db_item = db.query(CartItem).filter(CartItem.id == item_id).first()
        if db_item:
            update_data = item_update.dict(exclude_unset=True)
            for field, value in update_data.items():
                setattr(db_item, field, value)
            db.commit()
            db.refresh(db_item)
            return db_item
        return None
    
    @staticmethod
    def remove_item(db: Session, item_id: int) -> bool:
        db_item = db.query(CartItem).filter(CartItem.id == item_id).first()
        if db_item:
            db.delete(db_item)
            db.commit()
            return True
        return False
    
    @staticmethod
    def get_cart_items(db: Session, shopcart_id: int) -> List[CartItem]:
        return db.query(CartItem).filter(CartItem.shopcart_id == shopcart_id).all()
