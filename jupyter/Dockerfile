FROM python:3.12.4-slim

# Set the working directory in the container
WORKDIR /app

COPY requirements.txt .

# Install Jupyter Lab
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir jupyterlab folium mapclassify

# Copy the notebooks into the container
COPY notebooks /app/notebooks


# Copy the Jupyter configuration file
COPY jupyter_lab_config.py /root/.jupyter/jupyter_lab_config.py

# Expose the Jupyter Lab port
EXPOSE 8888

# Start Jupyter Lab
CMD ["jupyter", "lab", "--ip=0.0.0.0", "--port=8888", "--no-browser", "--allow-root"]