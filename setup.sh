#!/bin/bash

# Exit on error
set -e

# Variables
TOOL_NAME="macvdmtool"
DEST_PATH="/usr/local/bin/$TOOL_NAME"
SOURCE_PATH="$(pwd)/$TOOL_NAME/macvdmtool"  # Change this if your binary is elsewhere
SHELL_CONFIG="$HOME/.zshrc"  # Change to .bash_profile if needed

echo "➡️ Installing DFU Master..."

# Copy to /usr/local/bin
if [ ! -f "$SOURCE_PATH" ]; then
  echo "❌ Error: $SOURCE_PATH not found."
  exit 1
fi

sudo cp "$SOURCE_PATH" "$DEST_PATH"
sudo chmod +x "$DEST_PATH"
sudo xattr -rd com.apple.quarantine "$DEST_PATH"
echo "✅ Copied, made executable, and cleared Gatekeeper quarantine."

# Ensure /usr/local/bin is in PATH
if [[ ":$PATH:" != *":/usr/local/bin:"* ]]; then
  echo "➕ Adding /usr/local/bin to your PATH in $SHELL_CONFIG"
  echo 'export PATH="/usr/local/bin:$PATH"' >> "$SHELL_CONFIG"
  echo "ℹ️ Please run: source $SHELL_CONFIG"
fi

# Add to sudoers for passwordless use
  echo "$(whoami) ALL=(ALL) NOPASSWD: /usr/local/bin/macvdmtool *" | sudo tee /private/etc/sudoers.d/macvdmtool > /dev/null
  sudo chmod 440 /private/etc/sudoers.d/macvdmtool
  echo "✅ Added sudoers entry"

# Final test
echo "🚀 Running test command: $TOOL_NAME"
sudo "$TOOL_NAME" || echo "ℹ️ If macvdmtool doesn't run, try sudo $TOOL_NAME dfu"

echo "✅ Done."
