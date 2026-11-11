# ──────────────────────────────────────────────────────────
# Stage 1: Build
# ──────────────────────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

# Install dependencies (separate layer for cache efficiency)
COPY package.json package-lock.json ./
RUN npm ci

# Copy source and build
COPY . .

# VITE_API_BASE_URL can be overridden at build time:
#   docker build --build-arg VITE_API_BASE_URL=https://api.mysite.com ...
ARG VITE_API_BASE_URL=http://localhost:8000
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
# The public site (Next.js): non-admins and old user links are sent there.
ARG VITE_SITE_URL=http://localhost:3000
ENV VITE_SITE_URL=$VITE_SITE_URL

RUN npm run build

# ──────────────────────────────────────────────────────────
# Stage 2: Serve with nginx
# ──────────────────────────────────────────────────────────
FROM nginx:1.27-alpine AS runtime

# Remove default nginx content
RUN rm -rf /usr/share/nginx/html/*

# Copy built assets from the builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# nginx config that supports React Router (client-side routing)
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
