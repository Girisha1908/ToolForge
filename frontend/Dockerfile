# Local/dev-grade image (see TOOLFORGE_PLAN.md Phase 3). Not hardened for production.

# --- Build stage ---
FROM node:20-alpine AS build

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .

# VITE_API_BASE_URL is inlined into the static JS bundle at build time by Vite - it CANNOT be
# changed later via a container runtime env var. Pass it as a build arg per target environment.
ARG VITE_API_BASE_URL=http://localhost:8000
ARG VITE_TOOLFORGE_API_KEY=
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
ENV VITE_TOOLFORGE_API_KEY=$VITE_TOOLFORGE_API_KEY

RUN npm run build

# --- Serve stage ---
FROM nginx:alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
