#!/bin/bash
# Install system dependencies for Qt GUI testing on Linux

set -e

echo "Installing system dependencies for Qt GUI testing..."
echo

# Detect Linux distribution
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$NAME
    VER=$VERSION_ID
else
    echo "Cannot detect Linux distribution"
    exit 1
fi

# Function to check if running with sudo
check_sudo() {
    if [ "$EUID" -ne 0 ]; then 
        echo "This script requires sudo privileges. Please run with sudo:"
        echo "  sudo ./install_test_deps.sh"
        exit 1
    fi
}

# Ubuntu/Debian based distributions
install_debian() {
    echo "Installing dependencies for Debian/Ubuntu..."
    apt-get update
    apt-get install -y \
        xvfb \
        libxkbcommon-x11-0 \
        libxcb-icccm4 \
        libxcb-image0 \
        libxcb-keysyms1 \
        libxcb-randr0 \
        libxcb-render-util0 \
        libxcb-xinerama0 \
        libxcb-xfixes0 \
        libxcb-shape0 \
        libxcb-cursor0 \
        x11-utils \
        libglib2.0-0 \
        libgl1-mesa-glx \
        libgl1-mesa-dri \
        libdbus-1-3 \
        libxrender1 \
        libxi6 \
        libxrandr2 \
        libxss1 \
        libxtst6 \
        libnss3 \
        libasound2 \
        fonts-liberation \
        libgbm1
}

# Red Hat/CentOS/Fedora based distributions
install_redhat() {
    echo "Installing dependencies for Red Hat/CentOS/Fedora..."
    yum install -y \
        xorg-x11-server-Xvfb \
        xcb-util-keysyms \
        xcb-util-image \
        xcb-util-renderutil \
        xcb-util-wm \
        libxkbcommon-x11 \
        mesa-libGL \
        mesa-dri-drivers \
        dbus-libs \
        libXrender \
        libXi \
        libXrandr \
        libXScrnSaver \
        libXtst \
        nss \
        alsa-lib \
        liberation-fonts
}

# Arch Linux
install_arch() {
    echo "Installing dependencies for Arch Linux..."
    pacman -Sy --noconfirm \
        xorg-server-xvfb \
        libxkbcommon-x11 \
        xcb-util-keysyms \
        xcb-util-image \
        xcb-util-renderutil \
        xcb-util-wm \
        xcb-util-cursor \
        mesa \
        dbus \
        libxrender \
        libxi \
        libxrandr \
        libxss \
        libxtst \
        nss \
        alsa-lib \
        ttf-liberation
}

# Alpine Linux
install_alpine() {
    echo "Installing dependencies for Alpine Linux..."
    apk add --no-cache \
        xvfb \
        libxkbcommon \
        xcb-util-keysyms \
        xcb-util-image \
        xcb-util-renderutil \
        xcb-util-wm \
        mesa-gl \
        mesa-dri-gallium \
        dbus \
        libxrender \
        libxi \
        libxrandr \
        libxscrnsaver \
        libxtst \
        nss \
        alsa-lib \
        font-liberation
}

# Main installation logic
case "$OS" in
    "Ubuntu"|"Debian GNU/Linux"|"Linux Mint"|"Pop!_OS")
        check_sudo
        install_debian
        ;;
    "Fedora"|"CentOS Linux"|"Red Hat Enterprise Linux"|"Rocky Linux"|"AlmaLinux")
        check_sudo
        install_redhat
        ;;
    "Arch Linux"|"Manjaro Linux")
        check_sudo
        install_arch
        ;;
    "Alpine Linux")
        check_sudo
        install_alpine
        ;;
    *)
        echo "Unsupported distribution: $OS"
        echo
        echo "Please install the following packages manually:"
        echo "  - Xvfb (X Virtual Framebuffer)"
        echo "  - Qt platform dependencies (libxkbcommon-x11, xcb libraries)"
        echo "  - OpenGL libraries (Mesa)"
        echo "  - X11 utilities"
        exit 1
        ;;
esac

echo
echo "System dependencies installed successfully!"
echo
echo "Python dependencies can be installed with:"
echo "  pip install pytest pytest-qt pytest-xvfb"
echo
echo "To verify Xvfb installation:"
echo "  Xvfb -help"