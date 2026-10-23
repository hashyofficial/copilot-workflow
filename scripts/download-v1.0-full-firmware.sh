#!/usr/bin/env bash
# Release V 1.0 Final — download the complete verified Redmi Pad fastboot ROM.
# GitHub forbids release assets >=2 GiB; this helper produces one complete ZIP.
set -euo pipefail

ZIP="yunluo_MIUI14_Global_Build5_108Folders_GalleryRemoved_AVBDisabled_Fastboot.zip"
EXPECTED="c06c6b98772cca371d7cdcf7d69025e1539780eb2c279a54e0bb122e0a05ad7c"
RELEASE="https://github.com/hashyofficial/copilot-workflow/releases/download/yunluo-miui14-build5-complete-firmware"
PARTS_DIR=".yunluo_v1.0_download_parts"

printf '%s\n' "Release V 1.0 Final — Redmi Pad yunluo, MIUI 14 Global"
printf '%s\n' "Expected final firmware SHA-256: $EXPECTED"

if [[ -f "$ZIP" ]]; then
  actual="$(sha256sum "$ZIP" | awk '{print $1}')"
  if [[ "$actual" == "$EXPECTED" ]]; then
    echo "Existing complete firmware ZIP verified: $ZIP"
    exit 0
  fi
  echo "ERROR: existing $ZIP has a different SHA256; move it aside before retrying." >&2
  exit 1
fi

mkdir -p "$PARTS_DIR"
echo "Downloading and verifying the GitHub Release source transfer files..."
curl --fail --location --retry 8 --retry-all-errors --retry-delay 5 \
  --output "$PARTS_DIR/PARTS_SHA256.txt" "$RELEASE/PARTS_SHA256.txt"

if command -v aria2c >/dev/null 2>&1; then
  urls="$PARTS_DIR/download.urls"
  : > "$urls"
  for suffix in 000 001 002 003 004; do
    printf '%s/%s.part-%s\n' "$RELEASE" "$ZIP" "$suffix" >> "$urls"
  done
  aria2c -i "$urls" --dir="$PARTS_DIR" --continue=true \
    --max-concurrent-downloads=4 --max-connection-per-server=8 \
    --split=8 --min-split-size=4M --file-allocation=none \
    --auto-file-renaming=false --max-tries=15 --retry-wait=5 \
    --connect-timeout=25 --timeout=60 --summary-interval=20
else
  echo "aria2c not installed; downloading segments via curl (resumable)..."
  for suffix in 000 001 002 003 004; do
    url="$RELEASE/$ZIP.part-$suffix"
    curl --fail --location --retry 8 --retry-all-errors --retry-delay 5 \
      --continue-at - --output "$PARTS_DIR/$ZIP.part-$suffix" "$url"
  done
fi

(
  cd "$PARTS_DIR"
  sha256sum -c PARTS_SHA256.txt
)

echo "Assembling a single, complete firmware ZIP..."
cat "$PARTS_DIR/$ZIP.part-000" \
    "$PARTS_DIR/$ZIP.part-001" \
    "$PARTS_DIR/$ZIP.part-002" \
    "$PARTS_DIR/$ZIP.part-003" \
    "$PARTS_DIR/$ZIP.part-004" > "$ZIP.incomplete"

actual="$(sha256sum "$ZIP.incomplete" | awk '{print $1}')"
if [[ "$actual" != "$EXPECTED" ]]; then
  echo "ERROR: final ZIP SHA256 mismatch! Expected $EXPECTED; got $actual" >&2
  rm -f -- "$ZIP.incomplete"
  exit 1
fi
mv -- "$ZIP.incomplete" "$ZIP"
echo "ZIP SHA256 OK: $ZIP"
echo "Size: $(stat -c '%s' "$ZIP") bytes"
rm -rf -- "$PARTS_DIR"
echo "Transfer segments removed; only the complete ZIP remains."
echo "To extract: unzip -q \"$ZIP\""

if [[ "${EXTRACT:-0}" == "1" ]]; then
  unzip -q "$ZIP"
  echo "Firmware folder extracted successfully."
fi
