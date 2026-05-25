FROM python:3.12-alpine

WORKDIR /app
RUN mkdir -p /usr/share/nginx/html /usr/share/nginx/html/assets

# Static files
COPY index.html /usr/share/nginx/html/index.html
COPY paywall.html /usr/share/nginx/html/paywall.html
COPY datenschutz.html /usr/share/nginx/html/datenschutz.html
COPY dozenten.html /usr/share/nginx/html/dozenten.html
COPY sitemap.xml /usr/share/nginx/html/sitemap.xml
COPY robots.txt /usr/share/nginx/html/robots.txt
COPY assets/ /usr/share/nginx/html/assets/

# Server
COPY server.py /app/server.py

EXPOSE 8080
CMD ["python", "/app/server.py"]
