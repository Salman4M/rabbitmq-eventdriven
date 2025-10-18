#!/bin/bash

set -e

# Extract database host and port from DATABASE_URL
DB_HOST=$(echo $DATABASE_URL | sed -n 's/.*@\(.*\):.*/\1/p')
DB_PORT=$(echo $DATABASE_URL | sed -n 's/.*:\([0-9]*\)\/.*/\1/p')

echo "🔍 Waiting for PostgreSQL at $DB_HOST:$DB_PORT..."
while ! nc -z $DB_HOST $DB_PORT; do
  sleep 0.1
done
echo "✅ PostgreSQL started"

echo "🔍 Waiting for RabbitMQ..."
while ! nc -z $RABBITMQ_HOST $RABBITMQ_PORT; do
  sleep 0.1
done
echo "✅ RabbitMQ started"

echo "🔍 Waiting for Cart Service..."
while ! nc -z cart_service 8000; do
  sleep 0.1
done
echo "✅ Cart Service is reachable"

echo "📦 Running Alembic migrations..."
alembic upgrade head

echo "🚀 Starting FastAPI server with Uvicorn..."
uvicorn order_service.main:app --host 0.0.0.0 --port 8000 --reload
