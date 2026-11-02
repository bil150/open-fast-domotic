# The web application: nginx serving the built client, and forwarding /api to the server.
# Context: this folder (client/). It needs dist/, made by `npm run build` (already there in build/).
FROM nginx:alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY dist /usr/share/nginx/html

EXPOSE 80
