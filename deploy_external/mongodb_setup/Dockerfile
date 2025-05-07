FROM mongo:6.0

# Optional: Add custom MongoDB configuration
# COPY mongod.conf /etc/mongod.conf

# Default MongoDB port
EXPOSE 27017

# Start MongoDB with authentication enabled
CMD ["mongod", "--bind_ip_all"]