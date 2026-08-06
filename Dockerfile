FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
      unar aria2 ca-certificates && \
    rm -rf /var/lib/apt/lists/*
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY app.py /app/app.py
WORKDIR /app
EXPOSE 8770
CMD ["python","-u","app.py"]
