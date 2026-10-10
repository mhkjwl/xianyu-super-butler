#!/bin/bash
# 闲鱼超级管家 绿色版组装脚本
set -e

SRC="/c/Users/AO/Desktop/xianyu-super-butler-main"
REL="$SRC/release/xianyu-super-butler"
MP="$LOCALAPPDATA/ms-playwright"
NODE_SRC="/c/Users/AO/.workbuddy/binaries/node/versions/22.22.2-6/node.exe"

echo "=== 组装开始 $(date '+%H:%M:%S') ==="

echo "[1/6] 重置发布目录..."
rm -rf "$REL"
mkdir -p "$REL"

echo "[2/6] 复制主程序与支撑文件（dist）..."
cp -r "$SRC/dist_build/Start.dist/." "$REL/"
# 清理实验备份
rm -f "$REL/patchright/driver/package/browsers.json.bak-1243"
echo "    dist 复制完成"

echo "[3/6] 复制 Chromium 浏览器（完整版 + headless shell）..."
mkdir -p "$REL/playwright"
cp -r "$MP/chromium-1223" "$REL/playwright/"
echo "    chromium-1223 完成"
cp -r "$MP/chromium_headless_shell-1223" "$REL/playwright/"
echo "    chromium_headless_shell-1223 完成"

echo "[4/6] 复制 Node.js 运行时..."
mkdir -p "$REL/node"
cp "$NODE_SRC" "$REL/node/node.exe"
echo "    node.exe 完成"

echo "[5/6] 复制资源文件..."
cp -r "$SRC/static" "$REL/static"
cp "$SRC/global_config.yml" "$REL/global_config.yml"
cp "$SRC/packaging/start.bat" "$REL/start.bat"
echo "    资源完成"

echo "[6/6] 结构校验..."
echo "--- 顶层 ---"
ls "$REL" | head -20
echo "--- 关键文件 ---"
for f in "xianyu-butler.exe" "start.bat" "global_config.yml" "node/node.exe" \
         "static/index.html" "static/xianyu_js_version_2.js" \
         "playwright/chromium-1223/chrome-win64/chrome.exe" \
         "playwright/chromium_headless_shell-1223/chrome-headless-shell-win64/chrome-headless-shell.exe" \
         "patchright/driver/package/browsers.json" \
         "playwright/driver/package/browsers.json"; do
  if [ -e "$REL/$f" ]; then echo "  OK  $f"; else echo "  MISSING  $f"; fi
done
echo ""
echo "=== 总大小 ==="
du -sh "$REL"
echo "=== 组装完成 $(date '+%H:%M:%S') ==="
