# Build frontend
FROM node:20-alpine AS frontend-build
WORKDIR /app/client
COPY client/package*.json ./
RUN npm ci
COPY client ./
RUN npm run build

# Production image
FROM python:3.11-slim
WORKDIR /app

# Install Python dependencies
COPY server/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy server code
COPY server ./

# Copy frontend build
COPY --from=frontend-build /app/client/dist ./public

# Create data directories
RUN mkdir -p data/characters data/worldbooks data/presets data/chats data/images data/audio

EXPOSE 7412
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7412"]
