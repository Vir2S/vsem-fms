from core.logging import setup_logging
from server.server import Server


setup_logging()

# Create and run the server
server = Server()
server.run_server()
