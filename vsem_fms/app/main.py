from vsem_fms.app.core.logging import setup_logging
from vsem_fms.app.server.server import Server


setup_logging()

# Create server
server = Server()
app = server.server

if __name__ == "__main__":
    # Run server
    server.run_server()
