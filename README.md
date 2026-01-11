# Quick start

Forward local port 8080 to remote host port 80

```bash
uv run python main.py --listen-port 8080 --target-address example.com --target-port 80
```

Forward local port 9000 to localhost port 3000

```bash
uv run python main.py --listen-port 9000 --target-address 127.0.0.1 --target-port 3000
```

Forward local interface and port 9000 to localhost port 3000

```bash
uv run python main.py --listen-host 0.0.0.0 --listen-port 9000 --target-address 127.0.0.1 --target-port 3000
```

Proxy HTTP traffic

```bash
uv run python main.py --listen-port 8080 --target-address httpbin.org --target-port 80
```

Proxy HTTPS traffic (note: this won't decrypt SSL)
```bash
uv run python main.py --listen-port 8443 --target-address secure.example.com --target-port 443
```