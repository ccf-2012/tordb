# Stage 1: Build frontend
FROM node:24-alpine AS builder
WORKDIR /app/frontend

# Copy package files and install dependencies
COPY frontend/package*.json ./
RUN npm install

# Copy the rest of the frontend code and build
COPY frontend/ .
# Create React App builds to a 'build' folder by default
RUN npm run build

# Stage 2: Create final python application
FROM python:3.13-slim
WORKDIR /app

# Install netcat for health checks
RUN apt-get update && apt-get install -y netcat-openbsd && rm -rf /var/lib/apt/lists/*

# Copy the entire tordb directory
COPY . .

# Install Python dependencies from the backend directory
RUN pip install --no-cache-dir -r backend/requirements.txt

# Make the entrypoint script executable
RUN chmod +x backend/entrypoint.sh

# Copy built frontend from the builder stage
COPY --from=builder /app/frontend/build ./frontend/build

# Expose port and set the entrypoint
EXPOSE 6009
ENTRYPOINT ["/app/backend/entrypoint.sh"]
