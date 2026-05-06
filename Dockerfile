FROM nginx:alpine
COPY index.html /usr/share/nginx/html/index.html
COPY paywall.html /usr/share/nginx/html/paywall.html
COPY datenschutz.html /usr/share/nginx/html/datenschutz.html
COPY assets/ /usr/share/nginx/html/assets/

# nginx auf Railway-PORT konfigurieren (Standard 8080 falls nicht gesetzt)
RUN printf 'server {\n  listen ${PORT:-8080};\n  root /usr/share/nginx/html;\n  index index.html;\n  location / { try_files $uri $uri/ /index.html; }\n}\n' > /etc/nginx/conf.d/default.conf

EXPOSE 8080
CMD sh -c "sed -i \"s/\\\${PORT:-8080}/${PORT:-8080}/\" /etc/nginx/conf.d/default.conf && nginx -g 'daemon off;'"
