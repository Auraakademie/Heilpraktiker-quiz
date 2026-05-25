FROM nginx:alpine
COPY index.html /usr/share/nginx/html/index.html
COPY paywall.html /usr/share/nginx/html/paywall.html
COPY datenschutz.html /usr/share/nginx/html/datenschutz.html
COPY dozenten.html /usr/share/nginx/html/dozenten.html
COPY sitemap.xml /usr/share/nginx/html/sitemap.xml
COPY robots.txt /usr/share/nginx/html/robots.txt
COPY assets/ /usr/share/nginx/html/assets/

# nginx auf Railway-PORT konfigurieren (Standard 8080 falls nicht gesetzt)
# WICHTIG: sitemap.xml und robots.txt explizit servieren (nicht in SPA-Fallback)
RUN printf 'server {\n  listen ${PORT:-8080};\n  root /usr/share/nginx/html;\n  index index.html;\n  location = /sitemap.xml { add_header Content-Type application/xml; try_files $uri =404; }\n  location = /robots.txt { add_header Content-Type text/plain; try_files $uri =404; }\n  location / { try_files $uri $uri/ /index.html; }\n}\n' > /etc/nginx/conf.d/default.conf

EXPOSE 8080
CMD sh -c "sed -i \"s/\\\${PORT:-8080}/${PORT:-8080}/\" /etc/nginx/conf.d/default.conf && nginx -g 'daemon off;'"
