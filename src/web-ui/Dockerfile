FROM node:18-alpine AS build

WORKDIR /app

# Copy package files
COPY package.json ./

# Install dependencies
RUN npm install

# Copy the rest of the application
COPY . .

# Build the application
RUN npm run build

# Production stage
FROM node:18-alpine AS production
WORKDIR /app

# Install serve for production
RUN npm install -g serve

# Copy build files from the build stage
COPY --from=build /app/build ./build

# Expose port 3000
EXPOSE 3000

# Command to run the application
CMD ["serve", "-s", "build", "-l", "3000"]
