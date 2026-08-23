#!/bin/bash
set -e

TOOLS=/tools
BIN=$TOOLS/bin
TMP=$TOOLS/tmp

MACHINE=$1

#
# COMMON
#

step() {
    echo
    echo "============================================================"
    echo "  $1"
    echo "============================================================"
    echo
}

check_machine() {
    case "$MACHINE" in
        mac-x64|mac-arm|linux-x64)
            ;;
        *)
            echo "Unsupported machine: $MACHINE"
            exit 1
            ;;
    esac
}

#
# INSTALL JDK
#

install_jdks() {

    JDK_VERSIONS=(11 17 21 25)

    case "$MACHINE" in
        mac-x64)
            OS="mac"
            ARCH="x64"
            ;;
        mac-arm)
            OS="mac"
            ARCH="aarch64"
            ;;
        linux-x64)
            OS="linux"
            ARCH="x64"
            ;;
    esac

    for VERSION in "${JDK_VERSIONS[@]}"; do
        echo "Installing OpenJDK $VERSION ..."
        mkdir -p "$TOOLS/openjdk/jdk-$VERSION"
        curl -fL "https://api.adoptium.net/v3/binary/latest/$VERSION/ga/$OS/$ARCH/jdk/hotspot/normal/eclipse" -o "$TMP/jdk-$VERSION.tar.gz"
        tar -xzf "$TMP/jdk-$VERSION.tar.gz" -C "$TOOLS/openjdk/jdk-$VERSION" --strip-components=1
    done
}

#
# INSTALL ANDROID SDK
#

install_android_sdk() {

    mkdir -p "$TOOLS/android-sdk/cmdline-tools"

    case "$MACHINE" in
        mac-x64|mac-arm)
            ANDROID_CMDLINE_URL="https://dl.google.com/android/repository/commandlinetools-mac-14742923_latest.zip"
            ;;
        linux-x64)
            ANDROID_CMDLINE_URL="https://dl.google.com/android/repository/commandlinetools-linux-14742923_latest.zip"
            ;;
    esac

    curl -fL "$ANDROID_CMDLINE_URL" -o "$TMP/android.zip"
    rm   -rf "$TMP/android"
    unzip -q "$TMP/android.zip" -d "$TMP/android"
    mv       "$TMP/android/cmdline-tools" "$TOOLS/android-sdk/cmdline-tools/latest"

    SDKMANAGER="$TOOLS/android-sdk/cmdline-tools/latest/bin/sdkmanager"
    yes | "$SDKMANAGER" --licenses

    PACKAGES=("platform-tools")

    ANDROID_PLATFORMS=(31 32 33 34 35 36)
    for VERSION in "${ANDROID_PLATFORMS[@]}"; do
        PACKAGES+=("platforms;android-$VERSION")
    done

    BUILD_TOOLS=(31.0.0 32.0.0 33.0.2 34.0.0 35.0.0 36.0.0)
    for VERSION in "${BUILD_TOOLS[@]}"; do
        PACKAGES+=("build-tools;$VERSION")
    done

    CMAKE_VERSIONS=(3.22.1 3.31.0)
    for VERSION in "${CMAKE_VERSIONS[@]}"; do
        PACKAGES+=("cmake;$VERSION")
    done

    NDK_VERSIONS=(21.4.7075529)
    for VERSION in "${NDK_VERSIONS[@]}"; do
        PACKAGES+=("ndk;$VERSION")
    done

    "$SDKMANAGER" "${PACKAGES[@]}"
}

#
# INSTALL FLUTTER
#

install_flutter_sdk() {

    FLUTTER_VERSION="3.47.0"

    case "$MACHINE" in
        mac-x64)
            FLUTTER_OS="macos"
            FLUTTER_ARCHIVE="flutter_macos_${FLUTTER_VERSION}-stable.zip"
            ;;
        mac-arm)
            FLUTTER_OS="macos"
            FLUTTER_ARCHIVE="flutter_macos_arm64_${FLUTTER_VERSION}-stable.zip"
            ;;
        linux-x64)
            FLUTTER_OS="linux"
            FLUTTER_ARCHIVE="flutter_linux_${FLUTTER_VERSION}-stable.tar.xz"
            ;;
    esac

    curl -fL "https://storage.googleapis.com/flutter_infra_release/releases/stable/$FLUTTER_OS/$FLUTTER_ARCHIVE" -o "$TMP/flutter"

    case "$FLUTTER_ARCHIVE" in
        *.zip)
            unzip -q "$TMP/flutter" -d "$TOOLS"
            ;;
        *.tar.xz)
            tar -xf "$TMP/flutter" -C "$TOOLS"
            ;;
    esac

    ln -sf "$TOOLS/flutter/bin/flutter" "$BIN/flutter"
    ln -sf "$TOOLS/flutter/bin/dart"    "$BIN/dart"
}

#
# INSTALL NODE
#

install_node() {

    NODE_VERSION="22.14.0"

    case "$MACHINE" in
        mac-x64)
            NODE_OS="darwin"
            NODE_ARCH="x64"
            ;;
        mac-arm)
            NODE_OS="darwin"
            NODE_ARCH="arm64"
            ;;
        linux-x64)
            NODE_OS="linux"
            NODE_ARCH="x64"
            ;;
    esac

    mkdir -p "$TOOLS/node"
    curl -fL "https://nodejs.org/dist/v$NODE_VERSION/node-v$NODE_VERSION-$NODE_OS-$NODE_ARCH.tar.gz" -o "$TMP/node.tar.gz"
    tar -xzf "$TMP/node.tar.gz" -C "$TOOLS/node" --strip-components=1
}

#
# INSTALL SONAR SCANNER
#

install_sonar_scanner() {

    SONAR_SCANNER_VERSION="7.2.0.5079"

    case "$MACHINE" in
        mac-x64)
            SONAR_OS="macosx"
            SONAR_ARCH="x64"
            ;;
        mac-arm)
            SONAR_OS="macosx"
            SONAR_ARCH="aarch64"
            ;;
        linux-x64)
            SONAR_OS="linux"
            SONAR_ARCH="x64"
            ;;
    esac

    curl -fL "https://binaries.sonarsource.com/Distribution/sonar-scanner-cli/sonar-scanner-cli-${SONAR_SCANNER_VERSION}-${SONAR_OS}-${SONAR_ARCH}.zip" -o "$TMP/sonar-scanner.zip"
    rm   -rf "$TOOLS/sonar-scanner"
    unzip -q "$TMP/sonar-scanner.zip" -d "$TMP"
    mv       "$TMP/sonar-scanner-${SONAR_SCANNER_VERSION}-${SONAR_OS}-${SONAR_ARCH}" "$TOOLS/sonar-scanner"
    ln   -sf "$TOOLS/sonar-scanner/bin/sonar-scanner" "$BIN/sonar-scanner"
}

#
# INSTALL CDXGEN
#

install_cdxgen() {

    CDXGEN_VERSION="v13.0.0"

    case "$MACHINE" in
        linux-x64)
            CDXGEN_BINARY="cdxgen-linux-amd64"
            ;;
        mac-x64)
            CDXGEN_BINARY="cdxgen-darwin-amd64"
            ;;
        mac-arm)
            CDXGEN_BINARY="cdxgen-darwin-arm64"
            ;;
    esac

    curl -fL "https://github.com/cdxgen/cdxgen/releases/download/$CDXGEN_VERSION/$CDXGEN_BINARY" -o "$BIN/cdxgen"
    chmod +x "$BIN/cdxgen"
}

#
# INSTALL JFROG CLI
#

install_jfrog() {

    JFROG_VERSION="2.98.0"

    case "$MACHINE" in
        mac-x64)
            JFROG_OS="mac"
            JFROG_ARCH="386"
            ;;
        mac-arm)
            JFROG_OS="mac"
            JFROG_ARCH="arm64"
            ;;
        linux-x64)
            JFROG_OS="linux"
            JFROG_ARCH="amd64"
            ;;
    esac

    curl -fL "https://releases.jfrog.io/artifactory/jfrog-cli/v2/${JFROG_VERSION}/jfrog-cli-${JFROG_OS}-${JFROG_ARCH}/jfrog" -o "$BIN/jfrog"
    chmod +x "$BIN/jfrog"
}

#
# INSTALL MAVEN
#

install_maven() {

    MAVEN_VERSION="3.9.11"
    MAVEN_ARCHIVE="apache-maven-$MAVEN_VERSION-bin.tar.gz"

    mkdir -p "$TOOLS/maven"

    curl -fL "https://archive.apache.org/dist/maven/maven-3/$MAVEN_VERSION/binaries/$MAVEN_ARCHIVE" -o "$TMP/maven.tar.gz"
    tar -xzf "$TMP/maven.tar.gz" -C "$TOOLS/maven" --strip-components=1
    ln   -sf "$TOOLS/maven/bin/mvn" "$BIN/mvn"
}

#
# INSTALL COCOAPODS
#

#
# INSTALL RUBY
#

install_ruby() {

    RUBY_VERSION="3.3.7"

    case "$MACHINE" in
        mac-x64)
            RUBY_OS="darwin"
            RUBY_ARCH="x86_64"
            ;;
        mac-arm)
            RUBY_OS="darwin"
            RUBY_ARCH="arm64"
            ;;
        linux-x64)
            echo "Skipping Ruby: only required for CocoaPods on macOS."
            return
            ;;
    esac



    mkdir -p "$TOOLS/ruby"
    curl -fL "https://github.com/ruby/ruby-builder/releases/download/toolcache-ruby-${RUBY_VERSION}/ruby-${RUBY_VERSION}-${RUBY_OS}-${RUBY_ARCH}.tar.gz" -o "$TMP/ruby.tar.gz"
    tar -xzf "$TMP/ruby.tar.gz" -C "$TOOLS/ruby" --strip-components=1

    ln -sf "$TOOLS/ruby/bin/ruby" "$BIN/ruby"
    ln -sf "$TOOLS/ruby/bin/gem"  "$BIN/gem"

    # "$BIN/ruby" --version
    # "$BIN/gem"  --version
}

#
# INSTALL COCOAPODS
#

install_cocoapods() {

    case "$MACHINE" in
        mac-x64|mac-arm)
            ;;
        linux-x64)
            echo "Skipping CocoaPods: iOS tooling requires macOS/Xcode."
            return
            ;;
    esac

    COCOAPODS_VERSION="1.16.2"

    export GEM_HOME="$TOOLS/cocoapods"
    export GEM_PATH="$GEM_HOME"
    export PATH="$TOOLS/ruby/bin:$GEM_HOME/bin:$PATH"

    mkdir -p "$GEM_HOME"

    curl -fL   "https://rubygems.org/downloads/cocoapods-${COCOAPODS_VERSION}.gem" -o "$TMP/cocoapods.gem"
    "$BIN/gem"  install "$TMP/cocoapods.gem" --install-dir "$GEM_HOME" --no-document
    ln -sf      "$GEM_HOME/bin/pod" "$BIN/pod"

    # "$BIN/pod" --version
}

#
# MAIN
#

check_machine


# rm   -rf "$TOOLS"
mkdir -p "$TOOLS" "$BIN" "$TMP"

# install_jdks            
# install_android_sdk     
# install_flutter_sdk     
# install_node            
# install_sonar_scanner   
# install_cdxgen          
# install_jfrog           
# install_maven    
install_ruby       
install_cocoapods

#
# CLEANUP
#

step     "CLEANING UP ..."
rm   -rf "$TMP"
chown -R  tcuser:tcuser "$TOOLS"

#
# DONE
#

step "FLUTTER TOOLCHAIN INSTALLATION COMPLETE"

# Please, rember to set the ANDROID_HOME and
# the ANDROID_SDK_ROOT environment variables
# export ANDROID_HOME="$TOOLS/android-sdk"
# export ANDROID_SDK_ROOT="$TOOLS/android-sdk"