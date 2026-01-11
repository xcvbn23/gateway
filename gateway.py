import asyncio
import grp
import os
import pwd
import socket
import sys

from prometheus_client import CollectorRegistry, Counter, push_to_gateway

try:
    from systemd import daemon
except ImportError:
    daemon = None

from custom_logging import logger
from tcp_proxy_settings import TCPProxySettings


class TCPProxy:
    def __init__(self, settings: TCPProxySettings):
        self.server_socket = None

        self.listen_address = settings.listen_address
        self.listen_port = settings.listen_port
        self.target_address = settings.target_address
        self.target_port = settings.target_port
        self.pushgateway_url = settings.pushgateway_url
        self.user = settings.user
        self.group = settings.group
        self.source_socket_buffer_size = settings.source_socket_buffer_size
        self.proxy_server_socket_listen_backlog = (
            settings.proxy_server_socket_listen_backlog
        )

        # Prometheus metrics
        self.registry = CollectorRegistry()
        self.connections_total_metric = Counter(
            "gateway_tcp_proxy_connections_total",
            "Total number of connections handled",
            registry=self.registry,
        )
        self.bytes_transferred = Counter(
            "gateway_tcp_proxy_bytes_transferred_total",
            "Total bytes transferred",
            registry=self.registry,
        )

    async def start(self):
        """Start the proxy server"""
        try:
            server = await asyncio.start_server(
                self.handle_client,
                self.listen_address,
                self.listen_port,
                backlog=self.proxy_server_socket_listen_backlog,
            )

            # Drop privileges after binding if port < 1024 and user/group specified
            if self.listen_port < 1024 and (self.user or self.group):
                self.switch_user_and_group()

            logger.info(
                f"Proxying '{self.listen_address}:{self.listen_port} -> {self.target_address}:{self.target_port}'"
            )

            # Notify systemd that the service is ready (so watchdog starts expecting WATCHDOG pings)
            if daemon:
                try:
                    daemon.notify("READY=1")
                except Exception as e:
                    logger.error(f"Failed to notify systemd READY: {e}")

            # Start metrics pusher task if pushgateway_url is provided
            if self.pushgateway_url:
                logger.debug("Starting background Prometheus pushgateway task.")
                t = asyncio.create_task(self.push_metrics_periodically())
                t.add_done_callback(self._task_done)

            async with server:
                await server.serve_forever()

        except KeyboardInterrupt:
            print("\nShutting down proxy...")
        except Exception as e:
            print(f"Error starting proxy: {e}")
            sys.exit(1)

    async def push_metrics_periodically(self):
        """Push metrics to pushgateway every 60 seconds"""
        while True:
            await asyncio.sleep(60)
            try:
                if self.pushgateway_url is not None:
                    push_to_gateway(
                        self.pushgateway_url, job="tcp_proxy", registry=self.registry
                    )
                    logger.debug("Pushed metrics to pushgateway")
            except Exception as e:
                logger.error(f"Failed to push metrics: {e}")

    async def send_systemd_watchdog_notifications(self):
        while True:
            await asyncio.sleep(5)
            if daemon:
                daemon.notify("WATCHDOG=1")

    def _task_done(self, task: asyncio.Task):
        try:
            exc = task.exception()
            if exc:
                logger.error("Background task raised exception", exc_info=exc)
        except asyncio.CancelledError:
            pass

    def switch_user_and_group(self):
        """Switch to the specified user and group"""
        if self.group:
            try:
                gid = grp.getgrnam(self.group).gr_gid
                os.setgid(gid)
                logger.info(f"Running as group '{self.group}'")
            except KeyError:
                logger.error(f"Group '{self.group}' not found")
                sys.exit(1)

        if self.user:
            try:
                uid = pwd.getpwnam(self.user).pw_uid
                os.setuid(uid)
                logger.info(f"Running as user '{self.user}'")
            except KeyError:
                logger.error(f"User '{self.user}' not found")
                sys.exit(1)

    async def handle_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        """
        Handle a client connection by establishing a connection to the target server,
        configuring socket options for performance and reliability, and forwarding data
        bidirectionally between the client and the target.
        Args:
            reader (asyncio.StreamReader): Stream reader for the client connection.
            writer (asyncio.StreamWriter): Stream writer for the client connection.
        Returns:
            None
        Raises:
            Exception: Logs any exception that occurs during handling of the client connection.
        Side Effects:
            - Increments the total connections metric.
            - Configures TCP keep-alive and buffer options on both client and target sockets.
            - Forwards data between the client and the target server until the connection closes.
            - Closes both client and target connections upon completion or error.
        """
        logger.debug("Accepted connection")

        self.connections_total_metric.inc()

        target_reader = None
        target_writer = None

        try:
            # Connect to target server
            target_reader, target_writer = await asyncio.open_connection(
                self.target_address, self.target_port
            )

            # Enable TCP keep-alive to prevent idle drops (Linux-specific)
            sock = target_writer.get_extra_info("socket")
            if sock:
                # SO_KEEPALIVE
                # Enables TCP keep-alive probes on the socket.
                # This tells the OS to periodically send small "ping" packets over idle connections to keep them alive and detect if the remote end has gone away.
                # Without this, long-idle connections might be silently dropped by routers/firewalls.
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
                # TCP_KEEPIDLE
                # The idle timeout before keep-alive probes start.
                # If the connection sits idle (no data sent/received) for 30 seconds, the OS will begin sending keep-alive probes.
                # This is essentially the "initial timeout" for detecting dead connections.
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 30)
                # TCP_KEEPINTVL
                # The interval between individual keep-alive probes.
                # After the initial idle period TCP_KEEPIDLE, if no response is received, probes are sent every 5 seconds
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 5)
                # TCP_KEEPCNT
                # The maximum number of keep-alive probes to send before giving up.
                # If 3 probes are sent without a response, the connection is considered dead and will be closed.
                # This effectively sets an "overall timeout" for unresponsive connections (TCP_KEEPIDLE + (TCP_KEEPCNT * TCP_KEEPINTVL)).
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 3)
                # TCP_NODELAY
                # Disable Nagle's algorithm on target socket for lower latency
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                # SO_RCVBUF and SO_SNDBUF
                # Increase socket buffer sizes for better throughput
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1_024 * 1_024)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 1_024 * 1_024)

            # Disable Nagle's algorithm on client socket for lower latency
            client_sock = writer.get_extra_info("socket")
            if client_sock:
                # TCP_NODELAY
                # Disable Nagle's algorithm on client socket for lower latency
                client_sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                # SO_RCVBUF and SO_SNDBUF
                # Increase socket buffer sizes for better throughput
                client_sock.setsockopt(
                    socket.SOL_SOCKET, socket.SO_RCVBUF, 1_024 * 1_024
                )
                client_sock.setsockopt(
                    socket.SOL_SOCKET, socket.SO_SNDBUF, 1_024 * 1_024
                )

            # Forward data bidirectionally
            await asyncio.gather(
                self.forward_data(
                    reader,
                    target_writer,
                    f"{writer.get_extra_info('peername')} -> target",
                ),
                self.forward_data(
                    target_reader,
                    writer,
                    f"target -> {writer.get_extra_info('peername')}",
                ),
            )

        except Exception as e:
            logger.error(f"Error handling client: {e}")
        finally:
            if target_writer:
                target_writer.close()
                await target_writer.wait_closed()
            writer.close()
            await writer.wait_closed()

    async def forward_data(self, source_reader, dest_writer, direction):
        """Forward data from source to destination"""
        try:
            while True:
                data = await source_reader.read(self.source_socket_buffer_size)
                if not data:
                    break
                self.bytes_transferred.inc(len(data))
                dest_writer.write(data)
                await dest_writer.drain()
        except Exception as e:
            logger.error(f"Error forwarding data ({direction}): {e}")
