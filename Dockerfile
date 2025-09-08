# Stage 1: Build frontend
FROM node:24-alpine AS builder
WORKDIR /app/frontend

# Copy package files and install dependencies
COPY frontend/package*.json ./
RUN npm install

# Copy the rest of the frontend code and build
COPY frontend/ ./
# Create React App builds to a 'build' folder by default
RUN npm run build

# Stage 2: Create final python application
FROM python:3.13-slim
WORKDIR /app

# Install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ .

# Copy built frontend from the builder stage
# Assuming the backend is configured to serve files from a 'build' directory
COPY --from=builder /app/frontend/build ./build

# Expose port and run the application
EXPOSE 6009
CMD ["python", "run.py"]
