from django.shortcuts import render

# Create your views here.
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import User
from .serializers import UserSerializer, UserCreateSerializer
from .rabbitmq import rabbitmq_publisher
import logging

logger = logging.getLogger(__name__)

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    
    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        return UserSerializer
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # Publish to RabbitMQ if user is activated
        if user.is_activated:
            try:
                rabbitmq_publisher.publish_user_created(user)
            except Exception as e:
                logger.error(f'Failed to publish user created event: {e}')
                # Don't fail the request, just log the error
        
        headers = self.get_success_headers(serializer.data)
        return Response(
            UserSerializer(user).data,
            status=status.HTTP_201_CREATED,
            headers=headers
        )
    
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Activate a user and trigger shopcart creation"""
        user = self.get_object()
        
        if user.is_activated:
            return Response(
                {"message": "User is already activated"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user.is_activated = True
        user.save()
        
        # Publish to RabbitMQ
        try:
            rabbitmq_publisher.publish_user_created(user)
        except Exception as e:
            logger.error(f'Failed to publish user created event: {e}')
        
        return Response(UserSerializer(user).data)
    
    @action(detail=False, methods=['get'])
    def activated(self, request):
        """Get all activated users"""
        users = User.objects.filter(is_activated=True)
        serializer = self.get_serializer(users, many=True)
        return Response(serializer.data)