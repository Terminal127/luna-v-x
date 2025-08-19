# Stage 1: Build the Next.js application
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package.json and package-lock.json to leverage Docker cache
COPY package.json package-lock.json ./

# Install dependencies
RUN npm ci

# Copy the rest of the application code
COPY . .
COPY .env.local ./.env.local

# Build the Next.js application
# Next.js build typically creates a .next folder
RUN npm run build

# Stage 2: Run the Next.js application in production
FROM node:20-alpine AS runner

WORKDIR /app

# Set production environment
ENV NODE_ENV production

# Copy necessary files from the builder stage
# .next folder contains the built application
# public folder contains static assets
# package.json and node_modules are needed for next start
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/.env.local ./.env.local
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./package.json

# Expose the port Next.js runs on by default
EXPOSE 3000

# Command to run the Next.js application
CMD ["npm", "start"]
