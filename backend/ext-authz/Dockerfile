# Runtime-only image; binary is built on the host (see scripts note in story):
#   cd backend/ext-authz && go build -o ext-authz .
FROM alpine:3.21
RUN adduser -D -u 2016 extauthz
COPY ext-authz /usr/local/bin/ext-authz
USER 2016
EXPOSE 50053
ENTRYPOINT ["/usr/local/bin/ext-authz"]
