FROM node:20-alpine@sha256:afdf98210b07b586eb71fa22ba2e432e058e4cd1304d31ed60888755b8c865fb AS frontend-build

WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM nginx:alpine@sha256:1f25fedd50aec27413031afb3a4f8ee4effcc9d843f6a76e81bfa92245ac5c06

COPY docker/nginx/default.conf.template /etc/nginx/templates/default.conf.template
COPY --from=frontend-build /build/dist /usr/share/nginx/html

EXPOSE 80 443
HEALTHCHECK --interval=15s --timeout=5s --start-period=5s --retries=5 \
  CMD wget --quiet --tries=1 --spider http://127.0.0.1/health/live || exit 1
