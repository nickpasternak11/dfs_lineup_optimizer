FROM node:14 as base

WORKDIR /app

COPY package.json package-lock.json ./

RUN npm install

# Keep source changes from being hidden by a stale layer while retaining the
# cached dependency installation above.
COPY . .

RUN npm run build

FROM nginx:alpine as service

COPY --from=0 /app/build /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]