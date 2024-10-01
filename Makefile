IMAGE_NAME = "dfs_optimizer"
CONTAINER_NAME = "dfs_optimizer"

# Build the Docker image
build:
	docker buildx build -t $(IMAGE_NAME) .

# Run the container
run: build
	docker run --rm $(IMAGE_NAME)

# Stop the running container
stop:
	docker stop $(CONTAINER_NAME)

# Remove the container
remove:
	docker rm $(CONTAINER_NAME)

# Clean up image
clean:
	docker rmi $(IMAGE_NAME)

# Rebuild and run the container
rebuild: stop remove clean build run