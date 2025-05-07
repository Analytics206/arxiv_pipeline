# Start from the CUDA base image
FROM nvidia/cuda:12.0.1-devel-ubuntu22.04 AS builder

# Install dependencies
RUN apt-get update && \
    apt-get install -y \
    build-essential \
    curl \
    git \
    pkg-config \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Rust
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

# Clone Qdrant repository
WORKDIR /qdrant
RUN git clone https://github.com/qdrant/qdrant.git .

# Build with GPU support
ENV CUDA=1
RUN cargo build --release --bin qdrant

# Final image
FROM nvidia/cuda:12.0.1-runtime-ubuntu22.04

# Copy the built Qdrant binary
COPY --from=builder /qdrant/target/release/qdrant /qdrant/qdrant
WORKDIR /qdrant

# Default ports
EXPOSE 6333 6334

# Starting Qdrant
CMD ["./qdrant"]
