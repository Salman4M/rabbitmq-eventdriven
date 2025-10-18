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
        self.exchange_name = 'user_events'
        self.queue_name = 'shopcart_user_created_queue'
        self.routing_key = 'user.created'
        
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
            
            # Declare exchange
            self.channel.exchange_declare(
                exchange=self.exchange_name,
                exchange_type='topic',
                durable=True
            )
            
            # Declare queue
            self.channel.queue_declare(
                queue=self.queue_name,
                durable=True
            )
            
            # Bind queue to exchange
            self.channel.queue_bind(
                exchange=self.exchange_name,
                queue=self.queue_name,
                routing_key=self.routing_key
            )
            
            self.channel.basic_qos(prefetch_count=1)
            logger.info('✅ Connected to RabbitMQ')
            logger.info(f'📨 Waiting for messages in queue: {self.queue_name}')
        except Exception as e:
            logger.error(f'❌ Failed to connect to RabbitMQ: {e}')
            raise
    
    def callback(self, ch, method, properties, body):
        try:
            message = json.loads(body.decode())
            logger.info(f'📥 Received message: {message}')
            
            # Create shopcart
            self.create_shopcart(message)
            
            # Acknowledge message
            ch.basic_ack(delivery_tag=method.delivery_tag)
            logger.info(f'✅ Message acknowledged')
        except Exception as e:
            logger.error(f'❌ Error processing message: {e}')
            # Reject and requeue the message
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
    
    def create_shopcart(self, user_data):
        db: Session = SessionLocal()
        try:
            # Check if shopcart already exists
            existing_cart = ShopcartCRUD.get_shopcart_by_user_id(
                db, user_data['user_id']
            )
            
            if existing_cart:
                logger.info(f'⚠️  Shopcart already exists for user_id: {user_data["user_id"]}')
                return
            
            # Create new shopcart
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
    
    def start_consuming(self):
        try:
            self.channel.basic_consume(
                queue=self.queue_name,
                on_message_callback=self.callback,
                auto_ack=False
            )
            logger.info('🚀 Starting to consume messages...')
            self.channel.start_consuming()
        except KeyboardInterrupt:
            logger.info('⏹️  Stopping consumer...')
            self.stop()
        except Exception as e:
            logger.error(f'❌ Error in consumer: {e}')
            raise
    
    def stop(self):
        if self.channel:
            self.channel.stop_consuming()
        if self.connection:
            self.connection.close()