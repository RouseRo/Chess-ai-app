#!/bin/sh
set -e

# Start main auth service on port 8002 (proxied via nginx, publicly reachable)
uvicorn auth-service.main:app --host 0.0.0.0 --port 8002 &

# Start admin auth service on port 8003 (Docker-internal only — no host port binding)
exec uvicorn auth-service.main:admin_app --host 0.0.0.0 --port 8003
