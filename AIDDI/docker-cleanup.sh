#!/bin/bash

# Docker Cleanup Script
# Removes all containers and images

echo "🧹 Starting Docker cleanup..."

# Stop all running containers
echo "🛑 Stopping all running containers..."
if [ "$(docker ps -q)" ]; then
    docker stop $(docker ps -q)
    echo "✅ All running containers stopped"
else
    echo "ℹ️  No running containers found"
fi

# Remove all containers (stopped and running)
echo "🗑️  Removing all containers..."
if [ "$(docker ps -aq)" ]; then
    docker rm $(docker ps -aq)
    echo "✅ All containers removed"
else
    echo "ℹ️  No containers found"
fi

# Remove all images
echo "🗑️  Removing all images..."
if [ "$(docker images -q)" ]; then
    docker rmi $(docker images -q) --force
    echo "✅ All images removed"
else
    echo "ℹ️  No images found"
fi

# Clean up any remaining volumes, networks, and build cache
echo "🧽 Performing system cleanup..."
docker system prune -a --volumes --force

echo "🎉 Docker cleanup complete!"
echo "📊 Current Docker status:"
echo "Containers: $(docker ps -a | wc -l | xargs expr -1 +)"
echo "Images: $(docker images | wc -l | xargs expr -1 +)"
