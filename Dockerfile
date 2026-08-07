FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
      unar aria2 ca-certificates && \
    rm -rf /var/lib/apt/lists/*
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY app.py /app/app.py
WORKDIR /app
EXPOSE 8770

# Als NON-ROOT laufen (uid 1000). Die gemounteten Volumes (/config, /roms, …) müssen dem
# Benutzer gehören, unter dem der Container läuft. Auf Unraid o. ä. per `--user 99:100`
# (bzw. compose `user:`) überschreiben, damit es zur Share-Ownership passt.
# / Run as non-root (uid 1000). Mounted volumes must be writable by the runtime user;
# override with `--user <uid>:<gid>` to match your host ownership.
RUN useradd -u 1000 -m -s /usr/sbin/nologin romseerr && chown -R romseerr /app
USER 1000

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
  CMD python -c "import urllib.request,os,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:'+os.environ.get('PORT','8770')+'/health',timeout=4).status==200 else 1)"

CMD ["python","-u","app.py"]
