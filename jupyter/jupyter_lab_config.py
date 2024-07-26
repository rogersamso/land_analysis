c = get_config()

# Disable the authentication token
c.ServerApp.token = ''
c.ServerApp.password = ''
c.ServerApp.disable_check_xsrf = True
c.ServerApp.open_browser = False

# Set IP to allow connections from any IP address
c.ServerApp.ip = '0.0.0.0'

# Set port for Jupyter Lab
c.ServerApp.port = 8888

# Do not open a browser by default
c.ServerApp.open_browser = False

# Allow root user to run Jupyter Lab
c.ServerApp.allow_root = True
