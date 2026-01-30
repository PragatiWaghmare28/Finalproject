FROM node:20-alpine AS builder
WORKDIR /app

# Install dependencies and build
COPY package*.json ./
COPY vite.config.js .
COPY index.html ./
COPY src ./src
COPY public ./public
RUN npm ci && npm run build

FROM nginx:stable-alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
