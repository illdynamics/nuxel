#!/bin/sh
# Compatibility entry point: all pre-play callers use the corrected helper.
exec /usr/lib/nuxel/nuxel-audio-warmup "$@"
