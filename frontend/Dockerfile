FROM oven/bun:1-alpine AS build
WORKDIR /app
COPY package.json bun.lock* ./
RUN bun install --frozen-lockfile
COPY . .
RUN bun run build

FROM nginx:alpine
RUN addgroup -S app && adduser -S -G app app \
 && touch /var/run/nginx.pid \
 && chown -R app:app /var/cache/nginx /var/run/nginx.pid /usr/share/nginx/html
COPY --from=build --chown=app:app /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
USER app
EXPOSE 80