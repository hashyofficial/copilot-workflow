#!/usr/bin/env bash
# Redmi Pad yunluo Release V 1.0 Final — retrieve ONE full firmware ZIP from GHCR.
# ORAS is an OCI artifact client: https://oras.land/docs/installation/
set -euo pipefail
IMAGE="ghcr.io/hashyofficial/redmi-pad-yunluo-miui-project-firmware:v1.0"
ZIP="yunluo_MIUI14_Global_Build5_108Folders_GalleryRemoved_AVBDisabled_Fastboot.zip"
EXPECTED="c06c6b98772cca371d7cdcf7d69025e1539780eb2c279a54e0bb122e0a05ad7c"
if ! command -v oras >/dev/null 2>&1; then
  echo "ORAS command not found. Install ORAS first from https://oras.land/docs/installation/" >&2
  exit 1
fi
if [ -e "$ZIP" ]; then
  echo "Existing ZIP found; refusing to overwrite it: $ZIP" >&2
  exit 1
fi
echo "Downloading single complete firmware ZIP from $IMAGE"
oras pull "$IMAGE"
echo "$EXPECTED  $ZIP" | sha256sum -c -
echo "Verified complete ZIP: $ZIP"
