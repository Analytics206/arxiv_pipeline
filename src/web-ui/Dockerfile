FROM node:24.18.1-alpine AS build

WORKDIR /app

# Copy package files together so dependency installation is reproducible
COPY package.json package-lock.json ./

# Install the exact locked dependencies
RUN npm ci

# Copy the rest of the application
COPY . .

# Build the application
RUN npm run build

# Production stage
FROM node:24.18.1-alpine AS production
WORKDIR /app

# Pin the production server so Docker builds stay reproducible.
RUN npm install -g serve@14.2.6

# Copy build files from the build stage
COPY --from=build /app/build ./build

# Expose port 3000
EXPOSE 3000

# Command to run the application
CMD ["serve", "-s", "build", "-l", "3000"]
