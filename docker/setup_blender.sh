#!/bin/bash
# setup_blender.sh - Installs Blender 4.3 and XFCE Desktop (VNC)
set -e

BLENDER_URL="https://download.blender.org/release/Blender4.3/blender-4.3.0-linux-x64.tar.xz"
INSTALL_DIR="/workspace/blender"
VNC_PASS="runpod"

echo "========================================"
echo "Blender & Desktop Setup"
echo "========================================"

# --- 1. Install Blender (Headless) ---
if [ ! -d "$INSTALL_DIR" ]; then
    echo "Installing Blender 4.3..."
    mkdir -p "$INSTALL_DIR"
    wget -qO /workspace/blender.tar.xz "$BLENDER_URL"
    tar -xf /workspace/blender.tar.xz -C "$INSTALL_DIR" --strip-components=1
    rm /workspace/blender.tar.xz
    echo "Blender installed to $INSTALL_DIR"
else
    echo "Blender already installed."
fi

# Add to PATH temporarily for this session or user
export PATH="$INSTALL_DIR:$PATH"
echo "Blender Version: $(blender --version | head -1)"

# --- 2. Install Desktop (GUI/VNC) ---
GUI_CHOICE="${1:-xfce}" # Default to xfce if not provided

echo "Configuring Desktop Environment: $GUI_CHOICE"
apt-get update > /dev/null

if [ "$GUI_CHOICE" == "kde" ]; then
    echo "Ensuring KDE Plasma packages..."
    # Force non-interactive to prevent timezone prompts etc
    DEBIAN_FRONTEND=noninteractive apt-get install -y kde-plasma-desktop tigervnc-standalone-server tigervnc-common dbus-x11 > /dev/null
    START_CMD="startplasma-x11"
else
    echo "Ensuring XFCE4 packages..."
    DEBIAN_FRONTEND=noninteractive apt-get install -y xfce4 xfce4-goodies tigervnc-standalone-server tigervnc-common dbus-x11 > /dev/null
    START_CMD="startxfce4"
fi

# Clean up
rm -rf /var/lib/apt/lists/*

# Setup VNC Password (idempotent)
mkdir -p ~/.vnc
echo "$VNC_PASS" | vncpasswd -f > ~/.vnc/passwd
chmod 600 ~/.vnc/passwd

# FORCE Update Startup Script (Critical for switching)
echo "Updating VNC startup script for $GUI_CHOICE..."
cat <<EOF > ~/.vnc/xstartup
#!/bin/sh
unset SESSION_MANAGER
unset DBUS_SESSION_BUS_ADDRESS
exec $START_CMD
EOF
chmod +x ~/.vnc/xstartup

echo "Desktop Environment configured."


# --- 3. Start VNC (Force Restart) ---
echo "Restarting VNC Server..."
# Kill if running to apply new xstartup
vncserver -kill :1 &> /dev/null || true
rm -f /tmp/.X1-lock /tmp/.X11-unix/X1

# Start fresh
vncserver :1 -geometry 1920x1080 -depth 24
echo "VNC Started on :1 (Port 5901)"

echo "========================================"
echo "Ready. "
echo "CLI Render: /workspace/blender/blender -b file.blend -a"
echo "GUI Access: Connect VNC to Port 5901 (Password: $VNC_PASS)"
echo "========================================"
