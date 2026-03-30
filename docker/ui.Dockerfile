# React UI Dockerfile
FROM node:20-slim

WORKDIR /app

# Copy package files
COPY packages/qobserva_ui_react/package*.json ./

# Install dependencies
RUN npm install

# Copy source code
COPY packages/qobserva_ui_react/ ./

# Expose port
EXPOSE 3000

# Start dev server (for development)
# For production, use: npm run build && npm run preview
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "3000"]
