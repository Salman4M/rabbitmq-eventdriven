import pika
import json
import logging
from decouple import config

logger = logging.getLogger(__name__)

class RabbitMQPublisher:
    def __init__(self):
        self.connection = None
        self.channel = None
        self.exchange_name = 'order_events'
        
        self.rabbitmq_host = config('RABBITMQ_HOST', default='localhost')
        self.rabbitmq_port = int(config('RABBITMQ_PORT', default=5672))
        self.rabbitmq_user = config('RABBITMQ_USER', default='admin')
        self.rabbitmq_password = config('RABBITMQ_PASSWORD', default='admin123')
    
    def connect(self):
        """Connect to RabbitMQ"""
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
            
            logger.info('✅ Connected to RabbitMQ (Publisher)')
        except Exception as e:
            logger.error(f'❌ Failed to connect to RabbitMQ: {e}')
            raise
    
    def publish_order_created(self, order_id: int, user_id: int, cart_id: int):
        """Publish order.created event"""
        try:
            if not self.channel or self.connection.is_closed:
                self.connect()
            
            message = {
                'event': 'order.created',
                'order_id': order_id,
                'user_id': user_id,
                'cart_id': cart_id,
                'timestamp': None  # Will be set as ISO format
            }
            
            from datetime import datetime
            message['timestamp'] = datetime.utcnow().isoformat()
            
            self.channel.basic_publish(
                exchange=self.exchange_name,
                routing_key='order.created',
                body=json.dumps(message),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # Persistent
                    content_type='application/json'
                )
            )
            
            logger.info(f'📤 Published order.created event for order_id: {order_id}')
        except Exception as e:
            logger.error(f'❌ Error publishing order.created: {e}')
    
    def publish_order_cancelled(self, order_id: int, user_id: int):
        """Publish order.cancelled event"""
        try:
            if not self.channel or self.connection.is_closed:
                self.connect()
            
            message = {
                'event': 'order.cancelled',
                'order_id': order_id,
                'user_id': user_id,
                'timestamp': None
            }
            
            from datetime import datetime
            message['timestamp'] = datetime.utcnow().isoformat()
            
            self.channel.basic_publish(
                exchange=self.exchange_name,
                routing_key='order.cancelled',
                body=json.dumps(message),
                properties=pika.BasicProperties(
                    delivery_mode=2,
                    content_type='application/json'
                )
            )
            
            logger.info(f'📤 Published order.cancelled event for order_id: {order_id}')
        except Exception as e:
            logger.error(f'❌ Error publishing order.cancelled: {e}')
    
    def close(self):
        """Close connection"""
        if self.connection and not self.connection.is_closed:
            self.connection.close()

# Singleton instance
rabbitmq_publisher = RabbitMQPublisher()