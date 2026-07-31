FROM node:20-alpine AS build
WORKDIR /app
COPY . .
RUN npm install && chmod +x node_modules/.bin/tsc
RUN npm run build
# Copy static assets to dist if not handled by build
RUN cp index.html dist/ || true
RUN cp admin.html dist/ || true
RUN cp mobile.html dist/ || true
RUN [ -d "assets" ] && cp -r assets dist/ || true
RUN cp chessboard.js dist/ || true
RUN cp chessboard.css dist/ || true
# Copy chess piece images to dist if not handled by build
RUN [ -d "img" ] && cp -r img dist/ || true

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
