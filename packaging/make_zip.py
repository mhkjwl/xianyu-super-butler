"""绿色版 zip 打包脚本（Python zipfile，确保 UTF-8 文件名标志位正确）。

用法: python make_zip.py
输出: release/xianyu-super-butler-portable-3.2.0.zip
"""
import os
import time
import zipfile

SRC = r"C:\Users\AO\Desktop\xianyu-super-butler-main\release"
ROOT = "xianyu-super-butler"
OUT = os.path.join(SRC, "xianyu-super-butler-portable-3.2.0.zip")

# 运行期目录：绝不进发布包（避免把测试/运行残留带给用户）
EXCLUDE_DIRS = {"logs", "data", "backups"}
# 根目录运行期日志（如 realtime.log，由后端运行时生成）
EXCLUDE_ROOT_SUFFIX = (".log",)

if os.path.exists(OUT):
    os.remove(OUT)

start = time.time()
count = 0
total_bytes = 0

with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
    for dirpath, dirnames, filenames in os.walk(os.path.join(SRC, ROOT)):
        rel_dir = os.path.relpath(dirpath, os.path.join(SRC, ROOT))
        top = rel_dir.split(os.sep)[0]
        if top in EXCLUDE_DIRS:
            dirnames[:] = []
            continue
        for fn in filenames:
            if top == "." and fn.lower().endswith(EXCLUDE_ROOT_SUFFIX):
                continue
            full = os.path.join(dirpath, fn)
            arc = os.path.relpath(full, SRC).replace(os.sep, "/")
            z.write(full, arc)
            count += 1
            total_bytes += os.path.getsize(full)
            if count % 300 == 0:
                print(f"  [{count} files] {time.time()-start:.0f}s", flush=True)

size = os.path.getsize(OUT)
print(f"DONE files={count} raw={total_bytes/1048576:.1f}MB zip={size/1048576:.1f}MB time={time.time()-start:.0f}s")
