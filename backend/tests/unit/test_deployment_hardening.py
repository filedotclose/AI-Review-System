import os
import re
import pytest

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
NGINX_CONF = os.path.join(ROOT_DIR, "nginx", "nginx.conf")
NGINX_DEFAULT_CONF = os.path.join(ROOT_DIR, "nginx", "conf.d", "default.conf")
DOCKER_COMPOSE = os.path.join(ROOT_DIR, "docker-compose.yml")
DEPLOY_AWS = os.path.join(ROOT_DIR, "deploy_aws.sh")
FRONTEND_API_CLIENT = os.path.join(ROOT_DIR, "frontend", "src", "lib", "api-client.ts")


def test_nginx_configuration_files_exist():
    assert os.path.isfile(NGINX_CONF), f"Missing {NGINX_CONF}"
    assert os.path.isfile(NGINX_DEFAULT_CONF), f"Missing {NGINX_DEFAULT_CONF}"


def test_nginx_rate_limiting_and_security_directives():
    with open(NGINX_CONF, "r", encoding="utf-8") as f:
        nginx_conf = f.read()

    with open(NGINX_DEFAULT_CONF, "r", encoding="utf-8") as f:
        default_conf = f.read()

    combined = nginx_conf + "\n" + default_conf

    # Verify rate limit zones exist
    assert "limit_req_zone" in combined
    assert "auth_limit" in combined, "Nginx must define an auth_limit zone for login protection"
    assert "api_limit" in combined, "Nginx must define an api_limit zone"
    assert "limit_req_status 429;" in combined, "Nginx must return HTTP 429 on rate limit breaches"

    # Verify buffer overflow mitigations
    assert "client_max_body_size" in combined, "Nginx must configure client_max_body_size"

    # Verify defensive headers
    assert "X-Frame-Options" in combined, "Missing anti-clickjacking header"
    assert "X-Content-Type-Options" in combined, "Missing anti-MIME sniffing header"
    assert "server_tokens off;" in combined, "Server tokens must be disabled to hide Nginx version"


def test_docker_compose_isolates_backend_and_frontend():
    with open(DOCKER_COMPOSE, "r", encoding="utf-8") as f:
        compose_content = f.read()

    # Nginx service must exist and map ports 80 and 443
    assert "nginx:" in compose_content
    assert '"80:80"' in compose_content
    assert '"443:443"' in compose_content

    # Backend maps 8000 for Swagger docs, while frontend remains isolated
    assert '"8000:8000"' in compose_content, "Backend port 8000 must be mapped for dedicated Swagger docs access"
    assert '"3000:3000"' not in compose_content, "Frontend port 3000 must NOT be exposed to host"

    # Celery worker must have --pool=solo to avoid multi-process RAM exhaustion on 1GB instance
    assert "--pool=solo" in compose_content, "Celery worker must use --pool=solo on free tier"


def test_deploy_aws_firewall_rules():
    with open(DEPLOY_AWS, "r", encoding="utf-8") as f:
        script = f.read()

    # Must NOT allow 3000 through UFW
    assert "ufw allow 3000" not in script, "UFW must not open port 3000 in production"
    assert "ufw allow 8000" in script, "UFW must allow port 8000 for Swagger docs inspection"

    # Must allow 80 and 443
    assert "ufw allow 80/tcp" in script
    assert "ufw allow 443/tcp" in script

    # Should install fail2ban for SSH defense
    assert "fail2ban" in script, "deploy_aws.sh should install fail2ban for SSH brute-force defense"


def test_frontend_api_client_relative_url_handling():
    with open(FRONTEND_API_CLIENT, "r", encoding="utf-8") as f:
        client_code = f.read()

    # When running in browser behind reverse proxy, baseUrl should default to relative /api/v1
    assert "/api/v1" in client_code
    assert "http://localhost:8000" not in client_code or "NEXT_PUBLIC_API_URL" in client_code


BACKEND_MAIN = os.path.join(ROOT_DIR, "backend", "app", "main.py")


def test_nginx_endpoint_routing_and_upstreams():
    with open(NGINX_DEFAULT_CONF, "r", encoding="utf-8") as f:
        default_conf = f.read()

    with open(NGINX_CONF, "r", encoding="utf-8") as f:
        nginx_conf = f.read()

    # Upstream declarations
    assert "upstream backend_api" in default_conf
    assert "upstream frontend_ui" in default_conf
    assert "server backend:8000" in default_conf
    assert "server frontend:3000" in default_conf

    # Health check routing to backend and nginx self-health (supports optional trailing slash)
    assert "location ~ ^/(health|healthz|api/health|api/v1/health)(?:/|$)" in default_conf
    assert "location = /nginx-health" in default_conf
    assert "location = /nginx-health/" in default_conf

    # Custom JSON error responses for API breaches and upstream failures
    assert "@rate_limit_exceeded" in default_conf
    assert "@api_gateway_error" in default_conf
    assert "@payload_too_large" in default_conf

    # Auth routes with strict rate limit
    assert "location ~ ^/api/(?:v1/)?auth(?:/|$)" in default_conf
    assert "zone=auth_limit" in default_conf

    # Block /docs, /redoc, /openapi.json on standard HTTP/HTTPS traffic (port 80/443)
    assert "location ~ ^/(docs|redoc|openapi\\.json" in default_conf
    assert "return 404;" in default_conf

    # General API prefix routing
    assert "location /api" in default_conf
    assert "zone=api_limit" in default_conf

    # Next.js static assets and PWA service worker with keepalive
    assert "/_next/static/" in default_conf
    assert "location ~ ^/(sw\\.js|workbox-" in default_conf

    # WebSocket connection upgrade and forwarded protocol support
    assert "map $http_upgrade $connection_upgrade" in nginx_conf
    assert "map $http_x_forwarded_proto $forwarded_proto" in nginx_conf
    assert "$connection_upgrade" in default_conf
    assert "$forwarded_proto" in default_conf


def test_backend_main_routes_and_health():
    with open(BACKEND_MAIN, "r", encoding="utf-8") as f:
        main_code = f.read()

    # Dual route registration for /api/v1 and /api
    assert 'app.include_router(api_router, prefix="/api/v1")' in main_code
    assert 'app.include_router(api_router, prefix="/api")' in main_code

    # Health check endpoints with and without trailing slash
    assert '@app.get("/health")' in main_code
    assert '@app.get("/health/")' in main_code
    assert '@app.get("/healthz")' in main_code
    assert '@app.get("/healthz/")' in main_code
    assert '@app.get("/api/health")' in main_code
    assert '@app.get("/api/health/")' in main_code
    assert '@app.get("/api/v1/health")' in main_code
    assert '@app.get("/api/v1/health/")' in main_code

    # Root endpoint aliases
    assert '@app.get("/")' in main_code
    assert '@app.get("/api")' in main_code
    assert '@app.get("/api/v1")' in main_code


def test_nginx_route_resolution_simulation():
    """
    Simulate Nginx location matching rules against all critical endpoints:
    1. Exact match (=)
    2. Regex match (~) in order of declaration
    3. Prefix match (/api, /_next/static/, /)
    """
    with open(NGINX_DEFAULT_CONF, "r", encoding="utf-8") as f:
        conf = f.read()

    # Extract regex patterns
    health_re = re.search(r'location\s+~\s+\^/([^ \t\r\n{]+)', conf).group(1)
    health_pat = re.compile(rf"^/{health_re}")

    auth_re = re.search(r'location\s+~\s+\^/api/([^ \t\r\n{]+)', conf).group(1)
    auth_pat = re.compile(rf"^/api/{auth_re}")

    docs_re = re.search(r'location\s+~\s+\^/([^ \t\r\n{]+docs[^ \t\r\n{]+)', conf).group(1)
    docs_pat = re.compile(rf"^/{docs_re}")

    pwa_re = re.search(r'location\s+~\s+\^/([^ \t\r\n{]+sw[^ \t\r\n{]+)', conf).group(1)
    pwa_pat = re.compile(rf"^/{pwa_re}")

    def route_request(uri: str) -> str:
        # 1. Exact match
        if uri in ("/nginx-health", "/nginx-health/"):
            return "nginx_internal_health"
        # 2. Preferential prefix
        if uri.startswith("/_next/static/"):
            return "frontend_static_cache"
        # 3. Regex matches
        if health_pat.search(uri):
            return "backend_health"
        if auth_pat.search(uri):
            return "backend_auth_strict"
        if docs_pat.search(uri):
            return "blocked_404"
        if pwa_pat.search(uri):
            return "frontend_pwa_nocache"
        # 4. Prefix matches
        if uri.startswith("/api"):
            return "backend_api_general"
        if uri.startswith("/"):
            return "frontend_ui"
        return "unrouted"

    # Health Checks (with & without trailing slash)
    for path in ["/health", "/health/", "/healthz", "/healthz/", "/api/health", "/api/health/", "/api/v1/health", "/api/v1/health/"]:
        assert route_request(path) == "backend_health", f"Failed to route health path: {path}"

    assert route_request("/nginx-health") == "nginx_internal_health"
    assert route_request("/nginx-health/") == "nginx_internal_health"

    # High-Security Auth Endpoints
    for path in [
        "/api/v1/auth", "/api/v1/auth/", "/api/v1/auth/login", "/api/v1/auth/pin-login",
        "/api/v1/auth/email-login", "/api/v1/auth/me", "/api/v1/auth/logout", "/api/v1/auth/refresh",
        "/api/auth", "/api/auth/", "/api/auth/login"
    ]:
        assert route_request(path) == "backend_auth_strict", f"Failed to route auth path: {path}"

    # Documentation & OpenAPI blocked on port 80/443
    for path in [
        "/docs", "/docs/", "/redoc", "/redoc/", "/openapi.json",
        "/api/docs", "/api/v1/docs", "/api/redoc", "/api/v1/redoc",
        "/api/openapi.json", "/api/v1/openapi.json"
    ]:
        assert route_request(path) == "blocked_404", f"Failed to block docs path on port 80: {path}"

    # Business Domain API Endpoints
    for path in [
        "/api", "/api/", "/api/v1", "/api/v1/",
        "/api/v1/dpr", "/api/v1/dpr/123", "/api/v1/dpr/123/verify",
        "/api/v1/fuel", "/api/v1/fuel/summary", "/api/v1/fuel-register",
        "/api/v1/petty-cash", "/api/v1/petty-cash/expense", "/api/v1/petty_cash",
        "/api/v1/attendance", "/api/v1/attendance/workers", "/api/v1/attendance/gang",
        "/api/v1/brief", "/api/v1/brief/daily", "/api/v1/brief/today", "/api/v1/brief/history", "/api/v1/brief/generate"
    ]:
        assert route_request(path) == "backend_api_general", f"Failed to route general api path: {path}"

    # Frontend Static & PWA Assets
    assert route_request("/_next/static/chunks/main.js") == "frontend_static_cache"
    assert route_request("/sw.js") == "frontend_pwa_nocache"
    assert route_request("/workbox-f1770938.js") == "frontend_pwa_nocache"
    assert route_request("/manifest.json") == "frontend_pwa_nocache"

    # Frontend Web Application Navigation
    for path in ["/", "/login", "/dpr", "/petty-cash", "/attendance", "/brief"]:
        assert route_request(path) == "frontend_ui", f"Failed to route UI page: {path}"

