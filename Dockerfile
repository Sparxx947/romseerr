FROM python:3.14-slim
# p7zip-full fuer den Umbau aus der Oberflaeche (#593): `unar` allein reicht nicht — der
# Wegwerf-Container hat `p7zip` bisher bei jedem Start nachinstalliert, und ohne 7z bliebe
# ein Teil der Archive im vollen Umbau liegen, ohne dass es jemandem auffiele.
# EN: unar alone is not enough for the rebuild; without 7z part of the archives would
# silently stay packed.
RUN apt-get update && apt-get install -y --no-install-recommends \
      unar aria2 ca-certificates p7zip-full && \
    rm -rf /var/lib/apt/lists/*
COPY requirements.txt /app/requirements.txt
# --no-deps: requirements.txt fuehrt die VOLLE Huelle exakt gepinnt (#380). Ohne das
# holt pip Fehlendes selbst nach — in der neuesten Fassung, an der Datei vorbei, und
# zwei Bauten desselben Commits sind wieder zwei verschiedene Programme.
# `pip check` faengt eine unvollstaendige Liste HIER, statt sie zur Laufzeit als
# ImportError auffliegen zu lassen.
# EN: the file carries the full pinned closure, so pip must not resolve anything itself;
# `pip check` turns an incomplete list into a build failure instead of a runtime one.
RUN pip install --no-cache-dir --no-deps -r /app/requirements.txt && pip check
COPY app.py /app/app.py
# version.txt wird von release-please gepflegt und zur Laufzeit gelesen (/api/version).
COPY version.txt /app/version.txt
# Frontend: Vorlagen + statische Dateien (seit #73 nicht mehr in app.py eingebettet).
COPY templates/ /app/templates/
COPY static/ /app/static/
# BIBLIOTHEKSWERKZEUGE MITLIEFERN (#593). Sie lagen bisher nur im Repository, also musste
# jede Aenderung von Hand an zwei Orte kopiert werden — und genau das ging schief: Am
# 2026-08-14 war die Kopie auf dem Server drei PRs alt und kannte `--nur-beiwerk` gar
# nicht. Im Abbild sagt `/api/version` jetzt mit, welcher Stand dort liegt.
# EN: the library tools used to live only in the repo, so every change had to be copied to
# two places by hand; the server copy was three PRs behind and lacked a whole flag.
COPY contrib/library-tools/ /app/library-tools/
WORKDIR /app

# Build-Herkunft: vom CI per --build-arg gesetzt, im Quell-Checkout leer (dann meldet
# /api/version schlicht null statt zu raten).
ARG ROMSEERR_COMMIT=""
ARG ROMSEERR_BUILT_AT=""
ENV ROMSEERR_COMMIT=$ROMSEERR_COMMIT \
    ROMSEERR_BUILT_AT=$ROMSEERR_BUILT_AT
EXPOSE 8770
EXPOSE 8443

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
