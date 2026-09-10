#!/bin/bash


# Author:      Giorgio Daniele Luppina
# Date:        2026-09-07
# Description: This script allows to install Microsoft Azure CLI


AZURE_CLI_VERSION="2.90.0"
PYBIN_PATH="/usr/bin/python3.14"
AZURE_CLI_PACKAGE="https://github.com/Azure/azure-cli/releases/download/azure-cli-${AZ_VERSION}/azure-cli-${AZ_VERSION}-linux-x86_64.tar.gz"
AZURE_DIRECTORY="/tools/azure/azcli"

if [ ! -x "${PYTHON_BIN}" ]; then
    echo "Installing Python 3.14..."
    sudo dnf install -y python3.14
else
    echo "Python 3.14 already installed:"
    ${PYTHON_BIN} --version
fi

# Download the Azure CLI
mkdir -p "${TMP_DIR}"
echo "Downloading Azure CLI   ${AZ_VERSION}..."
curl -fL -o azure-cli.tar.gz "${AZ_URL}"

# Install the Azure CLI
sudo mkdir -p "${AZ_DIR}"
sudo tar -xzf azure-cli.tar.gz -C "${AZ_DIR}" --strip-components=1

# Configure the Azure CLI to use the Python interpreter
sudo sed -i "/PY_BIN=/a export AZ_PYTHON=\"\${AZ_PYTHON:-${PYTHON_BIN}}\"" "${AZ_DIR}/bin/az"

# Show if the patch is applied
echo 
echo
head -n 10 "${AZ_DIR}/bin/az"
echo
echo

#
# Test
#
"${AZ_DIR}/bin/az" version