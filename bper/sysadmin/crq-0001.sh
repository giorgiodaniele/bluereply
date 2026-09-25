#!/bin/bash

# Author:      Giorgio Daniele Luppina
# Date:        2026-23-09
# Description: Installing Azure CLI, Flutter SDK, and updating Jenkins. IT REQUIRES ROOT PRIVILEGES

USER=tcuser
GROUP=tcuser
JENKINS_RPM_VERSION=2.583-1
CDXGEN_VERSION=v13.0.0
PYTHON_VERSION=3.14
AZURE_CLI_VERSION=2.90.0
SONAR_SCANNER_VERSION=7.2.0.5079
FLUTTER_VERSIONS=(3.41.0 3.47.0)
JDK_VERSIONS=(8 11 17 21)

# Download and install the Azure CLI (Please fix /tools/azure/azcli/bin/az by setting export AZ_PYTHON="${AZ_PYTHON:/-/usr/bin/python3.14}")
curl    -fL   "https://github.com/Azure/azure-cli/releases/download/azure-cli-${AZURE_CLI_VERSION}/azure-cli-${AZURE_CLI_VERSION}-linux-x86_64.tar.gz" --output "azure-cli.tar.gz"
mkdir   -p     /tools/azure-cli
tar      -xzf "azure-cli.tar.gz" -C /tools/azure-cli --strip-components=1

# Download and install Python 3.14
dnf install -y python${PYTHON_VERSION} python${PYTHON_VERSION}-devel

# Download and install the CycloneDX Generator CLI
curl    -fL "https://github.com/cdxgen/cdxgen/releases/download/$CDXGEN_VERSION/cdxgen-linux-amd64" --output "cdxgen"
mkdir   -p   /tools/cdxgen
mv      "cdxgen" /tools/cdxgen/cdxgen

# Download and update RPM for Jenkins
curl -fL "https://get.jenkins.io/rpm/jenkins-${JENKINS_RPM_VERSION}.noarch.rpm" --output "jenkins-${JENKINS_RPM_VERSION}.rpm"
rpm  -i  "jenkins-${JENKINS_RPM_VERSION}.rpm"

# Download and install SonarQube scanner
curl    -fL   "https://binaries.sonarsource.com/Distribution/sonar-scanner-cli/sonar-scanner-cli-${SONAR_SCANNER_VERSION}-linux-x64.zip" --output "sonar-scanner.zip"
mkdir   -p    /tools/sonar-scanner
unzip   -q -o "sonar-scanner.zip" -d /tools/sonar-scanner/

mv    /tools/sonar-scanner/sonar-scanner-${SONAR_SCANNER_VERSION}-linux-x64/* /tools/sonar-scanner/
rmdir /tools/sonar-scanner/sonar-scanner-${SONAR_SCANNER_VERSION}-linux-x64

# Download and install Flutter SDKs
for FLUTTER_VERSION in "${FLUTTER_VERSIONS[@]}"; do
    curl  -fL "https://storage.googleapis.com/flutter_infra_release/releases/stable/linux/flutter_linux_${FLUTTER_VERSION}-stable.tar.xz" --output "flutter-${FLUTTER_VERSION}.tar.xz"
    mkdir -p  /tools/flutter/${FLUTTER_VERSION}
    tar   -xf "flutter-${FLUTTER_VERSION}.tar.xz" -C /tools/flutter/${FLUTTER_VERSION}
done

# Download and intall JDKs
for JDK_VERSION in "${JDK_VERSIONS[@]}"; do
    curl  -fL "https://api.adoptium.net/v3/binary/latest/${JDK_VERSION}/ga/linux/x64/jdk/hotspot/normal/eclipse" --output "jdk-${JDK_VERSION}.tar.gz"
    mkdir -p  /tools/jdk/${JDK_VERSION}
    tar   -xf "jdk-${JDK_VERSION}.tar.gz" -C /tools/jdk/${JDK_VERSION}
done


#
# Fix permissions
#
chown -R $USER:$GROUP /tools/