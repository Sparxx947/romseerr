FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
      unar aria2 ca-certificates && \
    rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir flask requests
COPY app.py /app/app.py
WORKDIR /app
EXPOSE 8770
CMD ["python","-u","app.py"]
