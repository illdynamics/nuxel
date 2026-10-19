#!/bin/bash
# Nuxel PWA Launcher for Flatpak
# Opens the PWA in a dedicated WebKit webview

APP_DIR="/app/nuxel"
APP_NAME="$(basename "$0")"

# Map binary name to app directory
case "$APP_NAME" in
    nuxel-launcher) APP="home" ;;
    nuxel-mail) APP="mail" ;;
    nuxel-calendar) APP="calendar" ;;
    *) echo "Unknown app: $APP_NAME"; exit 1 ;;
esac

APP_PATH="${APP_DIR}/${APP}/index.html"

if [ ! -f "$APP_PATH" ]; then
    echo "Error: App not found at $APP_PATH"
    exit 1
fi

# Launch using WebKitGTK webview
exec /app/bin/nuxel-pwa-launcher "file://${APP_PATH}"
