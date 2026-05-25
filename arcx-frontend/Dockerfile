# Use the official Node image based on Alpine Linux
FROM node:18-alpine

# Set the working directory
WORKDIR /app

# Copy package.json and package-lock.json
COPY package.json package-lock.json ./

# Install dependencies cleanly
RUN npm ci

# Copy the rest of the frontend source code
COPY . .

# Expose the Vite development port
EXPOSE 3000

# Start the Vite development server
# Note: vite.config.js must have host: true for this to be accessible outside the container
CMD ["npm", "run", "dev"]
