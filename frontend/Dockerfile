# =============================================================================
# FaceLogix Frontend Dockerfile
# Multi-stage build for React/Vite PWA
# =============================================================================

# -----------------------------------------------------------------------------
# Build Stage: Compile TypeScript and bundle assets
# -----------------------------------------------------------------------------
FROM node:20-alpine AS build

WORKDIR /app

# Install dependencies first for better caching
COPY package*.json ./
RUN npm ci --silent

# Copy source code and build
COPY . .
RUN npm run build

# -----------------------------------------------------------------------------
# Production Stage: Serve static files with nginx
# -----------------------------------------------------------------------------
FROM nginx:alpine AS production

# Copy built assets from build stage
COPY --from=build /app/dist /usr/share/nginx/html

# Copy custom nginx configuration for SPA routing
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Add non-root user for security
RUN addgroup -g 1001 -S appgroup && \
    adduser -u 1001 -S appuser -G appgroup && \
    chown -R appuser:appgroup /usr/share/nginx/html && \
    chown -R appuser:appgroup /var/cache/nginx && \
    chown -R appuser:appgroup /var/log/nginx && \
    touch /var/run/nginx.pid && \
    chown -R appuser:appgroup /var/run/nginx.pid

# Expose port 80
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost/health || exit 1

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
