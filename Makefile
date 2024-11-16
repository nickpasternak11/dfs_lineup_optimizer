export DOCKER_BUILDKIT=1

down:
	docker compose -f docker-compose.run.yml down

build:
	docker compose -f docker-compose.build.yml build

run: down build
	sudo mkdir -p /dfs_data
	sudo cp -r data/* /dfs_data
	docker compose -f docker-compose.run.yml up -d
