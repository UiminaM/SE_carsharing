FROM python:3.12-slim

WORKDIR /opt

COPY common /opt/common
RUN pip install --no-cache-dir /opt/common

COPY services/fleet-service /opt/app-src
RUN pip install --no-cache-dir /opt/app-src

WORKDIR /opt/app-src

EXPOSE 8004

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8004"]
