FROM node:18-alpine AS build
WORKDIR /app
# Copiar package files primero para cachear la instalación de dependencias
COPY package.json ./
COPY package-lock.json ./
COPY src ./src
COPY index.html ./
COPY vite.config.js ./
RUN if [ -f package-lock.json ]; then npm ci --silent; else npm install --silent; fi
RUN npm run build

FROM nginx:stable-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
