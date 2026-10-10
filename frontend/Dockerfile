# Build stage
FROM node:20-alpine AS builder

WORKDIR /app

COPY package*.json ./

RUN npm ci

COPY . .

# VITE_API_URL is baked into the bundle at build time, so it must arrive as a
# build argument — a runtime `-e VITE_API_URL=...` on this image would silently
# change nothing and the shop would call the wrong backend.
ARG VITE_API_URL
ENV VITE_API_URL=${VITE_API_URL}

RUN npm run build

# Production stage
FROM node:20-alpine

WORKDIR /app

RUN npm install -g http-server

COPY --from=builder /app/dist ./dist

EXPOSE 5173

# `--single` rewrites unknown paths to index.html so Vue Router routes like
# /category/women or /products/kurta load directly instead of 404ing.
CMD ["http-server", "dist", "-p", "5173", "--cors", "--single"]
