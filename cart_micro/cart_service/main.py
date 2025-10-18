# cart_micro/cart_service/main.py
from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import threading

# ✅ FIXED: Import from cart_service package
from cart_service.database import get_db, init_db
from cart_service.crud import ShopcartCRUD, CartItemCRUD
from cart_service.schemas import (
    ShopcartResponse,
    ShopcartSummary,
    CartItemCreate,
    CartItemUpdate,
    CartItemResponse
)
# ✅ FIXED: rabbitmq_consumer is at root level
import sys
sys.path.insert(0, '/app')
from rabbitmq_consumer import RabbitMQConsumer
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Shopcart Service API",
    description="Microservice for managing shopping carts",
    version="1.0.0"
)

# Initialize database and RabbitMQ consumer
@app.on_event("startup")
def startup_event():
    logger.info("🚀 Starting Shopcart Service...")
    init_db()
    logger.info("✅ Database initialized")
    
    # Start RabbitMQ consumer in a separate thread
    try:
        consumer = RabbitMQConsumer()
        consumer.connect()
        
        consumer_thread = threading.Thread(
            target=consumer.start_consuming,
            daemon=True
        )
        consumer_thread.start()
        logger.info("✅ RabbitMQ consumer started in background")
    except Exception as e:
        logger.error(f"❌ Failed to start RabbitMQ consumer: {e}")

@app.get("/", tags=["Health"])
def read_root():
    return {
        "service": "Shopcart Service",
        "status": "running",
        "version": "1.0.0"
    }

@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "healthy"}


# ==================== Shopcart Endpoints ====================

@app.get("/shopcarts/", response_model=List[ShopcartSummary], tags=["Shopcarts"])
def list_shopcarts(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get all shopcarts with summary information"""
    shopcarts = ShopcartCRUD.get_all_shopcarts(db, skip=skip, limit=limit)
    return shopcarts

@app.get("/shopcarts/{shopcart_id}", response_model=ShopcartResponse, tags=["Shopcarts"])
def get_shopcart(shopcart_id: int, db: Session = Depends(get_db)):
    """Get a specific shopcart by ID with all items"""
    shopcart = ShopcartCRUD.get_shopcart_by_id(db, shopcart_id)
    if not shopcart:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shopcart with id {shopcart_id} not found"
        )
    return shopcart

@app.get("/shopcarts/user/{user_id}", response_model=ShopcartResponse, tags=["Shopcarts"])
def get_shopcart_by_user(user_id: int, db: Session = Depends(get_db)):
    """Get shopcart by user ID"""
    shopcart = ShopcartCRUD.get_shopcart_by_user_id(db, user_id)
    if not shopcart:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shopcart for user {user_id} not found"
        )
    return shopcart

@app.delete("/shopcarts/{shopcart_id}", tags=["Shopcarts"])
def delete_shopcart(shopcart_id: int, db: Session = Depends(get_db)):
    """Delete a shopcart"""
    success = ShopcartCRUD.delete_shopcart(db, shopcart_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shopcart with id {shopcart_id} not found"
        )
    return {"message": "Shopcart deleted successfully"}

@app.post("/shopcarts/{shopcart_id}/clear", tags=["Shopcarts"])
def clear_shopcart(shopcart_id: int, db: Session = Depends(get_db)):
    """Clear all items from shopcart"""
    success = ShopcartCRUD.clear_shopcart(db, shopcart_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shopcart with id {shopcart_id} not found"
        )
    return {"message": "Shopcart cleared successfully"}


# ==================== Cart Items Endpoints ====================

@app.get("/shopcarts/{shopcart_id}/items", response_model=List[CartItemResponse], tags=["Cart Items"])
def get_cart_items(shopcart_id: int, db: Session = Depends(get_db)):
    """Get all items in a shopcart"""
    shopcart = ShopcartCRUD.get_shopcart_by_id(db, shopcart_id)
    if not shopcart:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shopcart with id {shopcart_id} not found"
        )
    return CartItemCRUD.get_cart_items(db, shopcart_id)

@app.post(
    "/shopcarts/{shopcart_id}/items",
    response_model=CartItemResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Cart Items"]
)
def add_item_to_cart(
    shopcart_id: int,
    item: CartItemCreate,
    db: Session = Depends(get_db)
):
    """Add an item to shopcart or update quantity if exists"""
    shopcart = ShopcartCRUD.get_shopcart_by_id(db, shopcart_id)
    if not shopcart:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shopcart with id {shopcart_id} not found"
        )
    
    cart_item = CartItemCRUD.add_item(db, shopcart_id, item)
    return cart_item

@app.patch("/items/{item_id}", response_model=CartItemResponse, tags=["Cart Items"])
def update_cart_item(
    item_id: int,
    item_update: CartItemUpdate,
    db: Session = Depends(get_db)
):
    """Update cart item quantity or price"""
    updated_item = CartItemCRUD.update_item(db, item_id, item_update)
    if not updated_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cart item with id {item_id} not found"
        )
    return updated_item

@app.delete("/items/{item_id}", tags=["Cart Items"])
def remove_item_from_cart(item_id: int, db: Session = Depends(get_db)):
    """Remove an item from cart"""
    success = CartItemCRUD.remove_item(db, item_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cart item with id {item_id} not found"
        )
    return {"message": "Item removed from cart successfully"}