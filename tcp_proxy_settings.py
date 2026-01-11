from pydantic import BaseModel, Field


class TCPProxySettings(BaseModel):
    listen_address: str = Field(default="127.0.0.1", description="Address to listen on")
    listen_port: int = Field(
        default=8080, description="Port to listen on", gt=0, le=65535
    )
    target_address: str = Field(
        default="127.0.0.1", description="Target address to forward to"
    )
    target_port: int = Field(
        default=80, description="Target port to forward to", gt=0, le=65535
    )
    pushgateway_url: str | None = Field(None, description="Prometheus pushgateway URL")
    user: str | None = Field(
        None, description="User to drop privileges to after binding (for ports < 1024)"
    )
    group: str | None = Field(
        None, description="Group to drop privileges to after binding (for ports < 1024)"
    )
    source_socket_buffer_size: int = Field(
        default=65_536,
        description="This reduces the number of system calls needed to read data, improving throughput.",
        gt=0,
        le=10_485_760,
    )
    proxy_server_socket_listen_backlog: int = Field(
        default=1024,
        description="This allows more incoming connections to queue up instead of being dropped under high load.",
    )
