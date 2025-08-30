# Stage 1: Build the Next.js application
FROM node:20-alpine AS builder
WORKDIR /app

# Copy package.json and package-lock.json to leverage Docker cache
COPY package.json package-lock.json ./

# Install dependencies
RUN npm ci

# Copy the rest of the application code
COPY . .

# Set environment variables for build time (NEXT_PUBLIC_* variables need to be available during build)
ENV NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
ENV NEXT_PUBLIC_TOOL_API_BASE_URL=http://localhost:9000/auth

# Build the Next.js application
RUN npm run build

# Stage 2: Run the Next.js application in production
FROM node:20-alpine AS runner
WORKDIR /app

# Set production environment
ENV NODE_ENV=production

# ENV NEXT_PUBLIC_API_BASE_URL=https://lunaai.app/apiforchatting
# ENV NEXT_PUBLIC_TOOL_API_BASE_URL=https://lunaai.app/authentication/

ENV NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
ENV NEXT_PUBLIC_TOOL_API_BASE_URL=http://localhost:9000/auth

# Copy necessary files from the builder stage
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./package.json

# Expose the port Next.js runs on by default
EXPOSE 3000

# Command to run the Next.js application
CMD ["npm", "start"]

# docker run   -d   -p 3000:3000   --name luna-frontend   --restart always   -e GOOGLE_CLIENT_ID="360970345352-2veevu4ulvpfd01de3gjjrtsmdfap4b9.apps.googleusercontent.com"   -e GOOGLE_CLIENT_SECRET="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"   -e NEXTAUTH_URL="https://lunaai.app"   -e GITHUB_CLIENT_ID="Ov23lijoHLvUs9frHPYZ"   -e GITHUB_CLIENT_SECRET="f851c07e29bd8c03402c2b42a2d97b28545cce75"   -e MONGODB_URI="mongodb+srv://terminalishere127:hello@cluster0.ezhgpwx.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"   -e NEXTAUTH_SECRET="4771d93e283747b2837bujbb9r5v"   the127terminal/frontend-app:latest

# docker run   -d   -p 3000:3000   --name luna-frontend   --restart always   -e GOOGLE_CLIENT_ID="360970345352-jhid0e7qippk59c6tpr9if7bujbb9r5v.apps.googleusercontent.com"   -e GOOGLE_CLIENT_SECRET="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"   -e NEXTAUTH_URL="http://localhost:3000"   -e GITHUB_CLIENT_ID="Ov23lijoHLvUs9frHPYZ"   -e GITHUB_CLIENT_SECRET="f851c07e29bd8c03402c2b42a2d97b28545cce75"   -e MONGODB_URI="mongodb+srv://terminalishere127:hello@cluster0.ezhgpwx.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"   -e NEXTAUTH_SECRET="4771d93e283747b2837bujbb9r5v"   the127terminal/frontend-app:latest
