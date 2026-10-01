# ===============================
# Builder Stage: Build React/Vite Frontend
# ===============================
FROM node:23.6.1-slim AS builder

WORKDIR /app

# Copy only what's needed for dependency install
COPY package*.json ./

# Install dependencies
RUN npm ci --no-audit --no-fund

# Copy the frontend source
COPY . .

# ---- Add build args for vite envs ----
ARG VITE_GRAPHQL_HTTP_URI
ARG VITE_GRAPHQL_WS_URI
ARG VITE_APP_NAME
ARG NODE_ENV=production

# ---- Make them available as environment variables ----
ENV VITE_GRAPHQL_HTTP_URI=$VITE_GRAPHQL_HTTP_URI
ENV VITE_GRAPHQL_WS_URI=$VITE_GRAPHQL_WS_URI
ENV VITE_APP_NAME=$VITE_APP_NAME
ENV NODE_ENV=$NODE_ENV

# ✅ Copy only the .env from the frontend directory (not parent)
# This ensures only the frontend env file is visible to Vite
COPY .env ./.env

# Optional sanity check — confirm Vite sees correct envs
RUN echo "Loaded env from /app/.env:" && cat .env || true

# ✅ Build using only the frontend env
# Make sure Vite runs from /app and doesn’t search parent dirs
RUN npm run build --prefix ./

# ===============================
# Final Stage: Serve with Nginx
# ===============================
FROM nginx:1.27.3-alpine-slim

# Copy built frontend
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy custom nginx site config
COPY nginx/nginx.conf /etc/nginx/conf.d/default.conf

# Fix permissions
RUN chown -R nginx:nginx /usr/share/nginx/html

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
