FROM rust:1.90-bookworm@sha256:3914072ca0c3b8aad871db9169a651ccfce30cf58303e5d6f2db16d1d8a7e58f AS probe
WORKDIR /build
COPY Cargo.toml Cargo.lock ./
COPY src ./src
COPY examples ./examples
COPY tests/harnesses/probe.rs tests/harnesses/probe.rs
# Register the lab-only probe in this disposable build, never in the crate.
RUN printf '\n[[example]]\nname = "probe"\npath = "tests/harnesses/probe.rs"\n' >> Cargo.toml \
    && cargo build --locked --offline --release --example probe

FROM node:24-bookworm-slim@sha256:0e0ff40c39bc087845bfb27465a0df4ea419520094bc35842ff83dd8cbe6f9b6
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*
ARG HARNESS_PACKAGE
ARG HARNESS_VERSION
COPY tests/harnesses/install.mjs tests/harnesses/harnesses.json /opt/
RUN node /opt/install.mjs ${HARNESS_PACKAGE} ${HARNESS_VERSION}
COPY --from=probe /build/target/release/examples/probe /usr/local/bin/agent-probe
COPY tests/harnesses/entrypoint.mjs /opt/entrypoint.mjs
COPY tests/harnesses/discover.mjs /opt/discover.mjs
USER node
WORKDIR /work
ENTRYPOINT ["node", "/opt/entrypoint.mjs"]
