# Client image with ScanAPI preinstalled, so the lab runs offline and the
# clients do not pip-install anything at start (upstream issue #2).
FROM kathara/base
RUN pip install --break-system-packages --no-cache-dir "curlify2<2.0.0,>=1.0.1" scanapi==2.13.2
