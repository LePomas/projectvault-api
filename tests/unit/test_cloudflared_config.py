from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

PROD_COMPOSE = Path("docker-compose.prod.yml")
CLOUDFLARED_CONFIG = Path("cloudflared/config.yml")


def test_cloudflared_command_reads_config_file() -> None:
    # Without --config, cloudflared silently drops all ingress rules and
    # returns 503 for every request.  Discovered when a systemd instance
    # running with --token only competed with the Docker container and
    # certain client IPv6 addresses consistently hashed to its connections.
    cmd = PROD_COMPOSE.read_text()
    assert "--config /etc/cloudflared/config.yml" in cmd


def test_cloudflared_command_uses_ipv4_edge() -> None:
    # Without --edge-ip-version 4, cloudflared opens tunnel connections via
    # IPv6 (auto mode).  Client IPv6 source addresses are then consistently
    # hashed to specific Cloudflare edge servers; if those servers hold no
    # active tunnel connection the response is 503.
    cmd = PROD_COMPOSE.read_text()
    assert "--edge-ip-version 4" in cmd


def test_cloudflared_token_comes_from_env_not_cli() -> None:
    # --token in the command line overrides --config and bypasses ingress
    # rules.  The token must come from the TUNNEL_TOKEN environment variable.
    cmd = PROD_COMPOSE.read_text()
    assert "TUNNEL_TOKEN" in cmd
    # Confirm it is wired as an env var, not embedded in the command string
    lines = [line for line in cmd.splitlines() if "command:" in line]
    assert all("--token" not in line for line in lines)


def test_cloudflared_config_protocol_is_http2() -> None:
    # QUIC (UDP) tunnel connections are dropped by CGNAT NAT mappings, causing
    # intermittent tunnel flaps and 503s with no CORS headers.  HTTP/2 (TCP)
    # keeps stable connections through the same CGNAT path.
    config = CLOUDFLARED_CONFIG.read_text()
    assert "protocol: http2" in config


def test_cloudflared_config_has_api_ingress_rule() -> None:
    config = CLOUDFLARED_CONFIG.read_text()
    assert "hostname: api.lepomas.xyz" in config
