# Use an official Node.js image
FROM node:18-alpine

# Set working directory
WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm install

# Copy project files from current context (FrontendDavis)
COPY . .

# Expose port for development server
EXPOSE 5173

# Start the development server on all network interfaces
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
