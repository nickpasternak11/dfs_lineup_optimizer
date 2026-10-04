FROM node:22-slim AS base

WORKDIR /app

# npm ci installs exactly what package-lock.json records.
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

COPY . .

# `make test` target; not part of the deployed image.
FROM base AS test
CMD ["npx", "vitest", "run"]

FROM base AS build
RUN npm run build

FROM nginx:alpine AS service

COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
