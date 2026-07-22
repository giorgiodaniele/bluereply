FROM golang:1.26.4-bookworm

# Install git
RUN apt-get update && apt-get install -y git

# Define working space
WORKDIR /app

# Clone openai CLI
RUN git clone https://github.com/openai/openai-cli.git