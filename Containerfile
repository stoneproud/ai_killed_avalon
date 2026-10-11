FROM python:3.11-slim-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends git perl openssl openssh-client bash ca-certificates && rm -rf /var/lib/apt/lists/*
COPY host.py challenge.py /opt/challenge/
COPY bot.py /opt/challenge/
COPY vendor /opt/challenge/vendor
ENV PYTHONDONTWRITEBYTECODE=1
WORKDIR /workspace
CMD ["bash"]
