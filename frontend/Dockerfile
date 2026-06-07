FROM node:18-alpine AS build

WORKDIR /app
COPY package.json ./
RUN npm install
COPY . .
RUN npm run build

# Production image with nginx
FROM nginx:alpine
COPY --from=build /app/build /usr/share/nginx/html

# Render nginx config from a template at startup so the backend hostname is
# configurable per environment. The nginx image runs envsubst over files in
# /etc/nginx/templates/*.template and writes the result to /etc/nginx/conf.d/.
# NGINX_ENVSUBST_FILTER limits substitution to BACKEND_HOST only, so nginx's
# own $variables (e.g. $host, $request_uri) are left untouched.
COPY nginx.conf /etc/nginx/templates/default.conf.template
ENV BACKEND_HOST=backend
ENV NGINX_ENVSUBST_FILTER=BACKEND_HOST

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
