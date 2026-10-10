"""绿色版组装脚本（Python 版，替代 assemble.sh，可在任意 Windows + venv 下运行）。

前置产物: dist_build/Start.dist/  (Nuitka standalone 编译输出)
浏览器缓存: %LOCALAPPDATA%/ms-playwright  (playwright install chromium 下载)
输出:      release/xianyu-super-butler/

用法: python packaging/assemble.py
"""
import json
import os
import shutil
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
DIST = PROJECT / "dist_build" / "Start.dist"
REL = PROJECT / "release" / "xianyu-super-butler"
MP = Path(os.environ["LOCALAPPDATA"]) / "ms-playwright"

# Node.js 候选路径：优先 workbuddy 托管版（较小），否则系统安装
NODE_CANDIDATES = [
    Path.home() / ".workbuddy" / "binaries" / "node" / "versions" / "22.22.2-6" / "node.exe",
    Path(r"C:\Program Files\nodejs\node.exe"),
]


def log(msg: str) -> None:
    print(msg, flush=True)


def choose_chromium() -> tuple[Path, Path]:
    """挑选要打包的浏览器目录（chromium + headless shell），取版本号最大的。"""
    def latest(prefix: str) -> Path:
        dirs = sorted(MP.glob(prefix), reverse=True)
        if not dirs:
            raise SystemExit(f"未找到 {prefix} 于 {MP}，请先运行: python -m playwright install chromium")
        return dirs[0]

    return latest("chromium-[0-9]*"), latest("chromium_headless_shell-[0-9]*")


def sync_patchright_revision() -> None:
    """从 playwright 的 browsers.json 读取 revision，同步到 patchright 的 browsers.json。

    patchright 1.63 期望 revision 1243，而 playwright 1.60 使用 1223。
    经实测 patchright 1.63 驱动 1223（Chromium 148）工作完全正常，
    统一指向 1223 可避免随包携带两份浏览器（省约 400MB）。
    """
    pw_js = REL / "playwright" / "driver" / "package" / "browsers.json"
    pr_js = REL / "patchright" / "driver" / "package" / "browsers.json"
    if not pw_js.exists() or not pr_js.exists():
        log("  [WARN] browsers.json 缺失，跳过 patchright revision 同步")
        return

    def chromium_entry(path: Path):
        data = json.loads(path.read_text(encoding="utf-8"))
        return data, {b["name"]: b for b in data["browsers"]}

    pw_data, pw = chromium_entry(pw_js)
    pr_data, pr = chromium_entry(pr_js)
    pw_rev = pw["chromium"]["revision"]
    pw_ver = pw["chromium"].get("browserVersion", "")

    changed = []
    for name in ("chromium", "chromium-headless-shell"):
        if name in pr and pr[name]["revision"] != pw_rev:
            pr[name]["revision"] = pw_rev
            if pw_ver:
                pr[name]["browserVersion"] = pw_ver
            changed.append(name)

    if changed:
        pr_js.write_text(json.dumps(pr_data, indent=2, ensure_ascii=False), encoding="utf-8")
        log(f"  已同步 patchright revision -> {pw_rev}（{', '.join(changed)}）")
    else:
        log(f"  patchright revision 已是 {pw_rev}，无需修改")


def main() -> None:
    log("=== 组装开始 ===")

    if not DIST.exists():
        raise SystemExit(f"未找到编译产物: {DIST}\n请先运行 Nuitka 编译（见 build_exe.bat）")

    chromium_dir, headless_dir = choose_chromium()
    log(f"  浏览器: {chromium_dir.name} + {headless_dir.name}")

    node_exe = next((p for p in NODE_CANDIDATES if p.exists()), None)
    if node_exe is None:
        raise SystemExit("未找到 node.exe（请安装 Node.js 或调整 NODE_CANDIDATES）")
    log(f"  Node.js: {node_exe}")

    log("[1/6] 重置发布目录...")
    if REL.exists():
        shutil.rmtree(REL)
    REL.mkdir(parents=True)

    log("[2/6] 复制主程序与支撑文件（dist）...")
    shutil.copytree(DIST, REL, dirs_exist_ok=True)
    for junk in REL.rglob("*.bak-*"):
        junk.unlink()

    log("[3/6] 复制 Chromium 浏览器...")
    pw_dir = REL / "playwright"
    pw_dir.mkdir(exist_ok=True)
    shutil.copytree(chromium_dir, pw_dir / chromium_dir.name, dirs_exist_ok=True)
    shutil.copytree(headless_dir, pw_dir / headless_dir.name, dirs_exist_ok=True)

    log("[4/6] 复制 Node.js 运行时...")
    (REL / "node").mkdir(exist_ok=True)
    shutil.copy2(node_exe, REL / "node" / "node.exe")

    log("[5/6] 复制资源文件...")
    shutil.copytree(PROJECT / "static", REL / "static", dirs_exist_ok=True)
    shutil.copy2(PROJECT / "global_config.yml", REL / "global_config.yml")
    shutil.copy2(PROJECT / "packaging" / "start.bat", REL / "start.bat")
    readme = PROJECT / "packaging" / "使用说明.txt"
    if readme.exists():
        shutil.copy2(readme, REL / "使用说明.txt")

    # GUI 壳（Nuitka onefile 编译产物）：用户双击进入图形界面
    gui_shell = PROJECT / "gui_build" / "XianyuSuperButler.exe"
    if gui_shell.exists():
        shutil.copy2(gui_shell, REL / "闲鱼超级管家.exe")
        log("  已加入 GUI 壳: 闲鱼超级管家.exe")
    else:
        log("  [WARN] 未找到 GUI 壳 gui_build/XianyuSuperButler.exe，将只提供 start.bat 启动")

    log("[6/6] 同步 patchright revision 并校验...")
    sync_patchright_revision()

    # 清理运行期残留（若组装后曾手动运行过测试，避免残留进入发布包）
    for junk in ("logs", "data", "backups"):
        p = REL / junk
        if p.is_dir():
            shutil.rmtree(p, ignore_errors=True)
            log(f"  已清理运行残留: {junk}/")
    for junk in REL.glob("*.log"):
        try:
            junk.unlink()
            log(f"  已清理运行残留: {junk.name}")
        except OSError:
            pass

    checks = [
        "闲鱼超级管家.exe",
        "xianyu-butler.exe",
        "start.bat",
        "global_config.yml",
        "node/node.exe",
        "static/index.html",
        "static/xianyu_js_version_2.js",
        f"playwright/{chromium_dir.name}/chrome-win64/chrome.exe",
        f"playwright/{headless_dir.name}/chrome-headless-shell-win64/chrome-headless-shell.exe",
        "patchright/driver/package/browsers.json",
        "playwright/driver/package/browsers.json",
    ]
    missing = [c for c in checks if not (REL / c).exists()]
    for c in checks:
        log(("  OK  " if (REL / c).exists() else "  MISSING  ") + c)
    if missing:
        raise SystemExit(f"组装校验失败，缺少: {missing}")

    log("=== 组装完成 ===")


if __name__ == "__main__":
    sys.exit(main())
