FROM node:22-bookworm-slim

# Install Python 3.11 and virtual-environment support; the base image provides Node.js 22.
RUN apt-get update \
  && apt-get install -y --no-install-recommends python3 python3-venv \
  && rm -rf /var/lib/apt/lists/*

# Copy uv from its official image.
COPY --from=ghcr.io/astral-sh/uv:0.9.26 /uv /uvx /bin/

WORKDIR /app

# Copy dependency manifests first to preserve Docker layer caching.
COPY package.json package-lock.json ./
COPY frontend/package.json frontend/package-lock.json ./frontend/
COPY backend/pyproject.toml backend/uv.lock ./backend/

# Install Node and Python dependencies.
RUN npm ci \
  && npm ci --prefix frontend \
  && cd backend && uv sync --frozen

# Copy application sources.
COPY . .

EXPOSE 3000 5001

# Start the frontend and backend together.
CMD ["npm", "run", "dev"]
