import pika
import json
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

class RabbitMQPublisher:
    def __init__(self):
        self.connection = None
        self.channel = None
        self.exchange_name = 'user_events'
        self.routing_key = 'user.created'
    
    def connect(self):
        try:
            credentials = pika.PlainCredentials(
                settings.RABBITMQ_USER,
                settings.RABBITMQ_PASSWORD
            )
            parameters = pika.ConnectionParameters(
                host=settings.RABBITMQ_HOST,
                port=settings.RABBITMQ_PORT,
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
            logger.info(' Connected to RabbitMQ')
        except Exception as e:
            logger.error(f' Failed to connect to RabbitMQ: {e}')
            raise
    
    def publish_user_created(self, user):
        try:
            if not self.channel or self.connection.is_closed:
                self.connect()
            
            message = {
                'user_id': user.id,
                'username': user.username,
                'email': user.email,
                'timestamp': user.created_at.isoformat()
            }
            
            self.channel.basic_publish(
                exchange=self.exchange_name,
                routing_key=self.routing_key,
                body=json.dumps(message),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # Make message persistent
                    content_type='application/json'
                )
            )
            logger.info(f' Published user created event for user_id: {user.id}')
        except Exception as e:
            logger.error(f' Error publishing message: {e}')
            # Don't raise exception, just log it
    
    def close(self):
        if self.connection and not self.connection.is_closed:
            self.connection.close()

# Create a singleton instance
rabbitmq_publisher = RabbitMQPublisher()