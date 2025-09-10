#!/bin/bash

# Wait for MySQL to be ready
echo "Waiting for MySQL to be ready..."
while ! nc -z mysql 3306; do
  sleep 1
done

echo "MySQL is up - executing command"

# Start the main application
exec python backend/run.py
