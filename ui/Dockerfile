FROM node:20-alpine AS build

WORKDIR /app/ui

COPY ui/package.json ./
RUN npm install

COPY ui/ ./

RUN npx vite build

FROM nginx:1.27-alpine

COPY ui/nginx/default.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/ui/dist /usr/share/nginx/html

EXPOSE 80