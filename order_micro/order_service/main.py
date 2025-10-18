from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import logging

from order_service.database import get_db, init_db
from order_service.crud import OrderCRUD
from order_service.schemas import OrderCreate, OrderUpdate, OrderResponse, OrderSummary
from cart_client import CartServiceClient
from rabbitmq_publisher import rabbitmq_publisher

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Order Service API",
    description="Microservice for managing orders",
    version="1.0.0"
)

# Initialize
@app.on_event("startup")
def startup_event():
    logger.info(" Starting Order Service...")
    init_db()
    logger.info(" Database initialized")
    
    try:
        rabbitmq_publisher.connect()
        logger.info(" RabbitMQ publisher connected")
    except Exception as e:
        logger.error(f" Failed to connect RabbitMQ publisher: {e}")

@app.on_event("shutdown")
def shutdown_event():
    rabbitmq_publisher.close()
    logger.info(" Order Service shutdown")

@app.get("/", tags=["Health"])
def read_root():
    return {
        "service": "Order Service",
        "status": "running",
        "version": "1.0.0"
    }

@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "healthy"}


# ==================== Order Endpoints ====================

@app.post("/orders", response_model=OrderResponse, status_code=status.HTTP_201_CREATED, tags=["Orders"])
async def create_order(
    order_data: OrderCreate,
    db: Session = Depends(get_db)
):
    """Create order from user's cart"""
    cart_client = CartServiceClient()
    
    # 1. Get cart items via HTTP (RPC)
    try:
        cart = await cart_client.get_cart_by_user(order_data.user_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Cart service unavailable: {str(e)}"
        )
    
    if not cart:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cart not found for user {order_data.user_id}"
        )
    
    if not cart.get('items') or len(cart['items']) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cart is empty. Cannot create order."
        )
    
    # 2. Create order in database
    order = OrderCRUD.create_order(
        db=db,
        user_id=order_data.user_id,
        cart_id=cart['id'],
        items=cart['items'],
        shipping_address=order_data.shipping_address
    )
    
    # 3. Publish order.created event (async via RabbitMQ)
    try:
        rabbitmq_publisher.publish_order_created(
            order_id=order.id,
            user_id=order.user_id,
            cart_id=cart['id']
        )
    except Exception as e:
        logger.error(f" Failed to publish order.created event: {e}")
        # Don't fail the request, cart will be cleared when RabbitMQ recovers
    
    logger.info(f" Order created: ID={order.id}, User={order.user_id}")
    return order

@app.get("/orders", response_model=List[OrderSummary], tags=["Orders"])
def list_orders(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get all orders"""
    orders = OrderCRUD.get_all_orders(db, skip=skip, limit=limit)
    
    # Convert to summary
    summaries = []
    for order in orders:
        summaries.append({
            "id": order.id,
            "user_id": order.user_id,
            "total_amount": order.total_amount,
            "status": order.status,
            "item_count": len(order.items),
            "created_at": order.created_at
        })
    
    return summaries

@app.get("/orders/{order_id}", response_model=OrderResponse, tags=["Orders"])
def get_order(order_id: int, db: Session = Depends(get_db)):
    """Get specific order by ID"""
    order = OrderCRUD.get_order_by_id(db, order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order with id {order_id} not found"
        )
    return order

@app.get("/orders/user/{user_id}", response_model=List[OrderResponse], tags=["Orders"])
def get_user_orders(
    user_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get all orders for a specific user"""
    orders = OrderCRUD.get_orders_by_user(db, user_id, skip=skip, limit=limit)
    return orders

@app.patch("/orders/{order_id}", response_model=OrderResponse, tags=["Orders"])
def update_order(
    order_id: int,
    order_update: OrderUpdate,
    db: Session = Depends(get_db)
):
    """Update order status or shipping address"""
    order = OrderCRUD.update_order(db, order_id, order_update)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order with id {order_id} not found"
        )
    return order

@app.post("/orders/{order_id}/cancel", tags=["Orders"])
def cancel_order(order_id: int, db: Session = Depends(get_db)):
    """Cancel an order"""
    order = OrderCRUD.get_order_by_id(db, order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order with id {order_id} not found"
        )
    
    success = OrderCRUD.cancel_order(db, order_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order cannot be cancelled (already shipped/delivered/cancelled)"
        )
    
    # Publish cancellation event
    try:
        rabbitmq_publisher.publish_order_cancelled(
            order_id=order.id,
            user_id=order.user_id
        )
    except Exception as e:
        logger.error(f" Failed to publish order.cancelled event: {e}")
    
    return {"message": "Order cancelled successfully", "order_id": order_id}