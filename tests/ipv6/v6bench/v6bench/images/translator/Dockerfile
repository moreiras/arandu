# Translator image for the nat64 and siit devices: TAYGA runs in userspace on a
# TUN device, so the lab needs no kernel module (Jool) and no privileged mode.
FROM kathara/base
RUN apt-get update -qq \
 && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq --no-install-recommends tayga \
 && rm -rf /var/lib/apt/lists/*
