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

    # Backend and frontend must NOT expose ports directly to host
    # Searching for raw port exposes: "8000:8000" or "3000:3000"
    assert '"8000:8000"' not in compose_content, "Backend port 8000 must NOT be exposed to host"
    assert '"3000:3000"' not in compose_content, "Frontend port 3000 must NOT be exposed to host"

    # Celery worker must have --pool=solo to avoid multi-process RAM exhaustion on 1GB instance
    assert "--pool=solo" in compose_content, "Celery worker must use --pool=solo on free tier"


def test_deploy_aws_firewall_rules():
    with open(DEPLOY_AWS, "r", encoding="utf-8") as f:
        script = f.read()

    # Must NOT allow 3000 or 8000 through UFW
    assert "ufw allow 3000" not in script, "UFW must not open port 3000 in production"
    assert "ufw allow 8000" not in script, "UFW must not open port 8000 in production"

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
