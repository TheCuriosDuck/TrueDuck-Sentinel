# Optional deployment foundation; this image is NOT a hardened public service.
# Build from the project root: docker build -f cloud_api/Dockerfile .
FROM python:3.12-slim
WORKDIR /app
COPY cloud_api/requirements.txt /app/cloud_api/requirements.txt
RUN pip install --no-cache-dir -r /app/cloud_api/requirements.txt

# Copy the code and dashboard, but NEVER the local database or token files.
COPY cloud_api/__init__.py cloud_api/app.py cloud_api/community.py /app/cloud_api/
COPY cloud_api/manage_owner.py cloud_api/backup_databases.py cloud_api/production.py /app/cloud_api/
COPY cloud_api/dashboard/ /app/cloud_api/dashboard/

# Leave the service in a non-root account. Mount a managed PostgreSQL database
# and use HTTPS at a trusted reverse proxy for any real hosted deployment.
RUN useradd --create-home --uid 10001 scamlens \
    && mkdir -p /app/cloud_api/data \
    && chown -R scamlens:scamlens /app/cloud_api/data
USER scamlens
EXPOSE 8080
CMD ["uvicorn", "cloud_api.app:app", "--host", "0.0.0.0", "--port", "8080"]
