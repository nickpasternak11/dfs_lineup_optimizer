FROM node:14 as base

WORKDIR /app

COPY package.json package-lock.json ./

RUN npm install

# Keep source changes from being hidden by a stale layer while retaining the
# cached dependency installation above.
COPY . .

# `make test` target; not part of the deployed image.
FROM base as test
ENV CI=true
CMD ["npm", "test", "--", "--watchAll=false"]

FROM base as build

RUN npm run build

FROM nginx:alpine as service

COPY --from=build /app/build /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
