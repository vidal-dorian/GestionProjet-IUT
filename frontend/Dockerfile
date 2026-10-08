FROM node:22-slim AS build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# Baked into the static bundle at build time (Vite reads env vars at build,
# not at container runtime). Empty string = same-origin API calls, which is
# what the bundled nginx.conf reverse-proxy expects.
ARG VITE_API_URL=""
ENV VITE_API_URL=$VITE_API_URL

RUN npm run build

# Variante officielle de nginx qui tourne sans root (écoute donc sur 8080,
# un port non privilégié). Branche 1.28 : la 1.27 n'est plus maintenue.
FROM nginxinc/nginx-unprivileged:1.28-alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY security-headers.conf /etc/nginx/snippets/security-headers.conf

EXPOSE 8080
