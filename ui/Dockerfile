FROM node:20-alpine AS build
WORKDIR /app
COPY . .
RUN npm install
RUN npm run build
# Copy index.html and any static assets to dist if not handled by build
RUN cp index.html dist/ || true
RUN [ -d "assets" ] && cp -r assets dist/ || true
RUN cp chessboard.js dist/ || true
RUN cp chessboard.css dist/ || true
# Copy chess piece images to dist if not handled by build
RUN [ -d "img" ] && cp -r img dist/ || true

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY player-selection.js /usr/share/nginx/html/
EXPOSE 80
