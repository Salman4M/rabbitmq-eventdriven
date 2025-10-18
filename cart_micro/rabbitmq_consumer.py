import pika
import json
import logging
from sqlalchemy.orm import Session
from cart_service.database import SessionLocal
from cart_service.crud import ShopcartCRUD
from cart_service.schemas import ShopcartCreate
from decouple import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RabbitMQConsumer:
    def __init__(self):
        self.connection = None
        self.channel = None
        self.user_exchange = 'user_events'
        self.order_exchange = 'order_events'
        self.user_queue = 'shopcart_user_created_queue'
        self.order_queue = 'shopcart_order_created_queue'
        
        self.rabbitmq_host = config('RABBITMQ_HOST', default='localhost')
        self.rabbitmq_port = int(config('RABBITMQ_PORT', default=5672))
        self.rabbitmq_user = config('RABBITMQ_USER', default='admin')
        self.rabbitmq_password = config('RABBITMQ_PASSWORD', default='admin')
    
    def connect(self):
        try:
            credentials = pika.PlainCredentials(
                self.rabbitmq_user,
                self.rabbitmq_password
            )
            parameters = pika.ConnectionParameters(
                host=self.rabbitmq_host,
                port=self.rabbitmq_port,
                credentials=credentials,
                heartbeat=600,
                blocked_connection_timeout=300
            )
            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()
            
            # Declare user events exchange and queue
            self.channel.exchange_declare(
                exchange=self.user_exchange,
                exchange_type='topic',
                durable=True
            )
            self.channel.queue_declare(queue=self.user_queue, durable=True)
            self.channel.queue_bind(
                exchange=self.user_exchange,
                queue=self.user_queue,
                routing_key='user.created'
            )
            
            # Declare order events exchange and queue
            self.channel.exchange_declare(
                exchange=self.order_exchange,
                exchange_type='topic',
                durable=True
            )
            self.channel.queue_declare(queue=self.order_queue, durable=True)
            self.channel.queue_bind(
                exchange=self.order_exchange,
                queue=self.order_queue,
                routing_key='order.created'
            )
            
            self.channel.basic_qos(prefetch_count=1)
            logger.info('✅ Connected to RabbitMQ (Cart Consumer)')
            logger.info(f'📨 Listening on queues: {self.user_queue}, {self.order_queue}')
        except Exception as e:
            logger.error(f'❌ Failed to connect to RabbitMQ: {e}')
            raise
    
    def callback_user_created(self, ch, method, properties, body):
        """Handle user.created events"""
        try:
            message = json.loads(body.decode())
            logger.info(f'📥 Received user.created: {message}')
            
            self.create_shopcart(message)
            
            ch.basic_ack(delivery_tag=method.delivery_tag)
            logger.info(f'✅ user.created processed')
        except Exception as e:
            logger.error(f'❌ Error processing user.created: {e}')
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
    
    def callback_order_created(self, ch, method, properties, body):
        """Handle order.created events - clear the cart"""
        try:
            message = json.loads(body.decode())
            logger.info(f'📥 Received order.created: {message}')
            
            cart_id = message.get('cart_id')
            order_id = message.get('order_id')
            
            if not cart_id:
                logger.error('❌ No cart_id in order.created event')
                ch.basic_ack(delivery_tag=method.delivery_tag)
                return
            
            # Clear the cart
            self.clear_cart(cart_id, order_id)
            
            ch.basic_ack(delivery_tag=method.delivery_tag)
            logger.info(f'✅ order.created processed - cart {cart_id} cleared')
        except Exception as e:
            logger.error(f'❌ Error processing order.created: {e}')
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
    
    def create_shopcart(self, user_data):
        """Create shopcart for new user"""
        db: Session = SessionLocal()
        try:
            existing_cart = ShopcartCRUD.get_shopcart_by_user_id(
                db, user_data['user_id']
            )
            
            if existing_cart:
                logger.info(f'⚠️ Shopcart already exists for user_id: {user_data["user_id"]}')
                return
            
            shopcart_data = ShopcartCreate(
                user_id=user_data['user_id'],
                username=user_data['username'],
                email=user_data['email']
            )
            shopcart = ShopcartCRUD.create_shopcart(db, shopcart_data)
            
            logger.info(f'🛒 Created shopcart (ID: {shopcart.id}) for user_id: {user_data["user_id"]}')
        except Exception as e:
            db.rollback()
            logger.error(f'❌ Error creating shopcart: {e}')
            raise
        finally:
            db.close()
    
    def clear_cart(self, cart_id: int, order_id: int):
        """Clear cart items after order is created"""
        db: Session = SessionLocal()
        try:
            success = ShopcartCRUD.clear_shopcart(db, cart_id)
            
            if success:
                logger.info(f'🗑️ Cleared cart {cart_id} for order {order_id}')
            else:
                logger.warning(f'⚠️ Cart {cart_id} not found or already empty')
        except Exception as e:
            db.rollback()
            logger.error(f'❌ Error clearing cart: {e}')
            raise
        finally:
            db.close()
    
    def start_consuming(self):
        """Start consuming messages from both queues"""
        try:
            # Register callbacks for both queues
            self.channel.basic_consume(
                queue=self.user_queue,
                on_message_callback=self.callback_user_created,
                auto_ack=False
            )
            
            self.channel.basic_consume(
                queue=self.order_queue,
                on_message_callback=self.callback_order_created,
                auto_ack=False
            )
            
            logger.info('🚀 Starting to consume messages...')
            self.channel.start_consuming()
        except KeyboardInterrupt:
            logger.info('⏹️ Stopping consumer...')
            self.stop()
        except Exception as e:
            logger.error(f'❌ Error in consumer: {e}')
            raise
    
    def stop(self):
        if self.channel:
            self.channel.stop_consuming()
        if self.connection:
            self.connection.close()