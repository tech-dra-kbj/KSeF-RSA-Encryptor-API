# Stable branch, floating minor so a rebuild picks up patch releases. The
# previous 1.27 pin went stale and dragged ~20 outdated Alpine packages with
# it, curl among them.
FROM nginx:1.30-alpine

# openssl for certificate provisioning, curl for the healthcheck. apk upgrade
# refreshes whatever the base image shipped stale.
RUN apk upgrade --no-cache \
    && apk add --no-cache openssl curl

COPY nginx.conf.template /etc/nginx/templates/default.conf.template
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# Certificates live on a mounted volume so they survive redeploys and can be
# collected from the host. See docker/proxy/entrypoint.sh.
VOLUME ["/etc/nginx/certs"]

EXPOSE 80 443

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["nginx", "-g", "daemon off;"]
