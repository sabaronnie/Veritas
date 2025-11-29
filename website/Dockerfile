FROM nginx:stable-alpine

# Remove default nginx content
RUN rm -rf /usr/share/nginx/html/*

# Copy site files
COPY . /usr/share/nginx/html

# Expose port 80
EXPOSE 80

# Use default nginx command
CMD ["nginx", "-g", "daemon off;"]
