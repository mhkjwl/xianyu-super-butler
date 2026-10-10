"""闲鱼超级管家 —— 桌面图形版启动器（GUI Shell）

用户双击本程序即可在自己的桌面窗口里使用全部功能，
不需要浏览器，也不需要 Docker / Python / Node（均已随包携带）。

工作流程：
1. 检查本地服务 http://127.0.0.1:8080 是否已运行
   - 已运行 -> 直接打开窗口进入管理界面
   - 未运行 -> 后台启动同目录的 xianyu-butler.exe（隐藏控制台窗口），
               先显示"正在启动"页，服务就绪后自动进入管理界面
2. 关闭窗口时询问：
   - 确定 = 完全退出（停止后台服务）
   - 取消 = 最小化到任务栏（系统托盘），后台继续挂机运行
3. 托盘图标右键菜单：
   - 打开主界面（重新显示窗口，双击图标同效）
   - 退出运行（停止后台服务并退出程序）

技术：pywebview + 系统自带 Microsoft Edge WebView2 渲染引擎 + pystray 托盘。

环境变量：
  GUI_SMOKE_TEST=<秒数>   自动化冒烟测试钩子：N 秒后模拟点击关闭按钮。
  GUI_SMOKE_CLOSE=quit|tray  冒烟测试时模拟选择的关闭方式（默认 quit）。
  GUI_HIDDEN=1            隐藏窗口运行（用于无打扰的自动化测试）。
"""

import os
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request

APP_TITLE = "闲鱼超级管家"
APP_URL = "http://127.0.0.1:8080"
HEALTH_URL = APP_URL + "/health"
BACKEND_NAME = "xianyu-butler.exe"
PID_FILE_NAME = ".gui_backend.pid"

# Windows 进程创建标志
CREATE_NO_WINDOW = 0x08000000

_QUIT_AFTER_CLOSE = {"quit": False}  # closing 事件里的决策：True=完全退出
_WATCHDOG_STARTED = {"v": False}
_WINDOW = {"ref": None}      # pywebview 窗口引用
_TRAY = {"icon": None}       # 托盘图标（进程内单例）
_SMOKE = bool(os.environ.get("GUI_SMOKE_TEST"))
_SMOKE_CLOSE = os.environ.get("GUI_SMOKE_CLOSE", "quit")  # 测试钩子: quit | tray
_HIDDEN = bool(os.environ.get("GUI_HIDDEN"))


def storage_dir() -> str:
    """固定的 WebView2 用户数据目录。

    必须固定一个稳定目录：pywebview 默认在系统临时目录建随机目录，
    频繁重启时容易出现目录冲突，导致 WebView2 渲染进程崩溃。
    """
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    path = os.path.join(base, "XianyuSuperButler", "webview2")
    os.makedirs(path, exist_ok=True)
    return path


def app_dir() -> str:
    """程序所在目录（即用户双击的 exe 所在目录）。

    注意：Nuitka onefile 模式下 sys.executable 指向临时解压目录，
    必须优先使用 Nuitka 记录的原始路径（__compiled__.containing_dir），
    否则会找不到同目录的 xianyu-butler.exe / playwright / data 等资源。
    """
    # 1) Nuitka 编译产物：原始 exe 所在目录（onefile 解压运行也准确）
    try:
        return os.path.abspath(__compiled__.containing_dir)
    except Exception:
        pass
    # 2) onefile 启动环境变量（备选）
    env_dir = os.environ.get("NUITKA_ONEFILE_DIRECTORY")
    if env_dir and os.path.isdir(env_dir):
        return env_dir
    # 3) frozen（standalone）或 onefile：sys.argv[0] 指向原始 exe
    if getattr(sys, "frozen", False):
        argv0 = sys.argv[0] if sys.argv else ""
        if argv0 and os.path.exists(argv0):
            return os.path.dirname(os.path.abspath(argv0))
        return os.path.dirname(os.path.abspath(sys.executable))
    # 4) 开发模式（python gui_launcher.py）
    return os.path.dirname(os.path.abspath(__file__))


def log(message: str) -> None:
    """简单日志：控制台 + logs/gui-launcher.log（便于用户排查）。"""
    print(f"[GUI] {message}", flush=True)
    try:
        log_dir = os.path.join(app_dir(), "logs")
        os.makedirs(log_dir, exist_ok=True)
        stamp = time.strftime("%Y-%m-%d %H:%M:%S")
        with open(os.path.join(log_dir, "gui-launcher.log"), "a", encoding="utf-8") as f:
            f.write(f"{stamp} | {message}\n")
    except Exception:
        pass


def health_ok(timeout: float = 2.0) -> bool:
    try:
        with urllib.request.urlopen(HEALTH_URL, timeout=timeout) as resp:
            return resp.status == 200
    except Exception:
        return False


def pid_file_path() -> str:
    return os.path.join(app_dir(), "data", PID_FILE_NAME)


def write_pid(pid: int) -> None:
    try:
        os.makedirs(os.path.dirname(pid_file_path()), exist_ok=True)
        with open(pid_file_path(), "w", encoding="ascii") as f:
            f.write(str(pid))
    except OSError:
        pass


def read_pid():
    try:
        with open(pid_file_path(), "r", encoding="ascii") as f:
            return int(f.read().strip())
    except Exception:
        return None


def start_backend() -> bool:
    """后台启动同目录的 xianyu-butler.exe（无控制台窗口）。"""
    exe = os.path.join(app_dir(), BACKEND_NAME)
    if not os.path.isfile(exe):
        log(f"未找到后端程序: {exe}")
        return False

    env = os.environ.copy()
    browsers_dir = os.path.join(app_dir(), "playwright")
    if os.path.isdir(browsers_dir):
        env["PLAYWRIGHT_BROWSERS_PATH"] = browsers_dir

    try:
        proc = subprocess.Popen(
            [exe],
            cwd=app_dir(),
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=CREATE_NO_WINDOW,
        )
        write_pid(proc.pid)
        log(f"已启动后端服务, PID={proc.pid}")
        return True
    except Exception as e:
        log(f"启动后端失败: {e}")
        return False


def wait_ready(timeout: float = 240.0) -> bool:
    start = time.time()
    while time.time() - start < timeout:
        if health_ok():
            return True
        time.sleep(1.0)
    return False


def is_backend_process(pid: int) -> bool:
    """检查 PID 是否确为后端的进程（避免误杀同 PID 的其他程序）。

    注：不用 tasklist 解析——中文系统的输出编码（GBK）易导致解析失败；
    psutil 直接读进程信息，跨语言环境稳定。
    """
    try:
        import psutil
        proc = psutil.Process(pid)
        return BACKEND_NAME.lower() in (proc.name() or "").lower()
    except Exception:
        return False


def stop_backend() -> None:
    """停止后端服务：优先用记录的 PID（校验进程名），否则按镜像名兜底。"""
    pid = read_pid()
    killed = False
    if pid and is_backend_process(pid):
        try:
            subprocess.run(
                ["taskkill", "/PID", str(pid), "/F"],
                capture_output=True, timeout=15,
                creationflags=CREATE_NO_WINDOW,
            )
            killed = True
            log(f"已停止后端服务, PID={pid}")
        except Exception as e:
            log(f"按 PID 停止失败: {e}")
    if not killed:
        try:
            subprocess.run(
                ["taskkill", "/IM", BACKEND_NAME, "/F"],
                capture_output=True, timeout=15,
                creationflags=CREATE_NO_WINDOW,
            )
            log("已按进程名停止后端服务")
        except Exception as e:
            log(f"兜底停止失败: {e}")
    try:
        os.remove(pid_file_path())
    except OSError:
        pass


def single_instance_guard():
    """防止重复双击开两个窗口：文件锁，进程退出自动释放。"""
    import msvcrt
    lock_path = os.path.join(app_dir(), "data", ".gui.lock")
    os.makedirs(os.path.dirname(lock_path), exist_ok=True)
    lock_file = open(lock_path, "a+b")
    try:
        msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
    except OSError:
        return None
    return lock_file  # 持有引用，防止被 GC


def show_error_box(title: str, message: str) -> None:
    """最底层兜底提示（不依赖 GUI 框架）。"""
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(None, message, title, 0x10)
    except Exception:
        print(f"{title}: {message}", file=sys.stderr)


# ==================== 系统托盘（任务栏通知区域） ====================

def load_tray_image():
    """加载托盘图标：优先程序目录 / onefile 解压目录里的 app.ico。"""
    from PIL import Image
    candidates = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "app.ico"),  # onefile 数据目录
        os.path.join(app_dir(), "app.ico"),                                     # 常规目录
    ]
    for p in candidates:
        if os.path.isfile(p):
            try:
                return Image.open(p)
            except Exception:
                continue
    # 兜底：纯色圆角图标
    from PIL import ImageDraw
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    ImageDraw.Draw(img).rounded_rectangle([(0, 0), (63, 63)], radius=14, fill=(91, 108, 255, 255))
    return img


def open_main_window() -> None:
    """托盘菜单：打开主界面（异步执行，避免阻塞托盘消息循环）。"""
    threading.Thread(target=_do_show, daemon=True).start()


def _do_show() -> None:
    w = _WINDOW.get("ref")
    if w is None:
        return
    try:
        w.show()
        w.restore()
        log("托盘：已打开主界面")
    except Exception as e:
        log(f"托盘：打开主界面失败 {e}")


def tray_quit(icon=None, item=None) -> None:
    """托盘菜单：退出运行（停止后台服务并退出程序）。"""
    log("托盘：退出运行")
    _QUIT_AFTER_CLOSE["quit"] = True
    try:
        if icon is not None:
            icon.stop()
    except Exception:
        pass
    _stop_backend_async()
    try:
        _WINDOW["ref"].destroy()
    except Exception:
        pass
    _start_watchdog()


def ensure_tray() -> None:
    """创建并启动托盘图标（进程内仅创建一次）。"""
    if _TRAY["icon"] is not None:
        return
    import pystray
    from pystray import Menu, MenuItem

    icon = pystray.Icon(
        "xianyu_super_butler",
        load_tray_image(),
        APP_TITLE,
        Menu(
            MenuItem("打开主界面", lambda i, it: open_main_window(), default=True),
            MenuItem("退出运行", lambda i, it: tray_quit(i, it)),
        ),
    )
    _TRAY["icon"] = icon
    threading.Thread(target=icon.run, daemon=True).start()
    log("已创建托盘图标（任务栏通知区域）")


def _safe_hide() -> None:
    """把窗口隐藏到托盘（独立线程执行，避免在 closing 回调里直接操作 UI）。"""
    time.sleep(0.15)
    try:
        _WINDOW["ref"].hide()
        log("窗口已最小化到任务栏（托盘）")
    except Exception as e:
        log(f"隐藏窗口失败: {e}")


LOADING_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<style>
  html, body { height: 100%; margin: 0; }
  body {
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    background: #0f1115; color: #e6e8ee;
    font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
  }
  .brand { font-size: 30px; font-weight: 600; letter-spacing: 2px; margin-bottom: 28px; }
  .spinner {
    width: 44px; height: 44px; border-radius: 50%;
    border: 3px solid rgba(140,160,255,.18); border-top-color: #7c9bff;
    animation: spin 0.9s linear infinite; margin-bottom: 24px;
  }
  @keyframes spin { to { transform: rotate(360deg); } }
  .tip { color: #9aa3b5; font-size: 14px; }
  .wait { color: #6b7488; font-size: 12px; margin-top: 10px; }
</style>
</head>
<body>
  <div class="brand">闲鱼超级管家</div>
  <div class="spinner"></div>
  <div class="tip">正在启动本地服务，请稍候…</div>
  <div class="wait">首次启动约需 10~30 秒，已等待 <span id="s">0</span> 秒</div>
  <script>
    var n = 0;
    setInterval(function () { document.getElementById('s').textContent = ++n; }, 1000);
  </script>
</body>
</html>"""


def error_html(message: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8">
<style>
  html, body {{ height: 100%; margin: 0; }}
  body {{
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    background: #0f1115; color: #e6e8ee;
    font-family: "Microsoft YaHei", "Segoe UI", sans-serif; padding: 40px; box-sizing: border-box;
  }}
  .title {{ font-size: 22px; font-weight: 600; margin-bottom: 16px; color: #ff8f8f; }}
  .msg {{ color: #b6bdcb; font-size: 14px; line-height: 1.9; text-align: center; max-width: 620px; }}
  .hint {{ color: #6b7488; font-size: 12px; margin-top: 26px; }}
</style></head>
<body>
  <div class="title">服务启动失败</div>
  <div class="msg">{message}</div>
  <div class="hint">请关闭本窗口后重新打开程序；若仍失败，请查看 logs 目录下的日志。</div>
</body>
</html>"""


def _exit_watchdog() -> None:
    """退出看门狗：窗口关闭后若进程因残留线程迟迟不退，强制结束。

    pywebview / WebView2 在个别环境下关闭流程可能残留后台线程，
    导致进程不退出。看门狗保证「关闭窗口后进程必然消失」的用户预期。
    """
    time.sleep(20)
    log("退出超时，强制结束进程")
    os._exit(0)


def _start_watchdog() -> None:
    if not _WATCHDOG_STARTED["v"]:
        _WATCHDOG_STARTED["v"] = True
        threading.Thread(target=_exit_watchdog, daemon=True).start()


_STOP_DONE = threading.Event()


def _stop_backend_async() -> None:
    """异步停止后端，并在完成后置位事件（主流程退出前会等待它）。"""
    def run() -> None:
        try:
            stop_backend()
        finally:
            _STOP_DONE.set()
    threading.Thread(target=run, daemon=True).start()


def main() -> int:
    import webview

    lock = single_instance_guard()
    if lock is None:
        show_error_box(
            APP_TITLE,
            "闲鱼超级管家已在运行中。\n\n"
            "如果界面上看不到它，请在任务栏右下角的通知区域（托盘）\n"
            "找到本程序的小图标，右键选择「打开主界面」。",
        )
        return 0

    # 允许页面内下载文件（导出卡密、订单等）
    webview.settings["ALLOW_DOWNLOADS"] = True

    window = webview.create_window(
        APP_TITLE,
        html=LOADING_HTML,
        width=1280,
        height=800,
        min_size=(1024, 680),
        background_color="#0f1115",
        hidden=_HIDDEN,
    )
    _WINDOW["ref"] = window

    def on_closing() -> bool:
        """关闭窗口时的决策：
        确定 = 完全退出；取消 = 最小化到任务栏（托盘托管）。
        """
        if _SMOKE:
            if _SMOKE_CLOSE == "tray":
                ensure_tray()
                threading.Thread(target=_safe_hide, daemon=True).start()
                return False  # 阻止关闭，窗口转入托盘
            # quit：完整模拟"完全退出"（含停止后端）
            _QUIT_AFTER_CLOSE["quit"] = True
            _start_watchdog()
            _stop_backend_async()
            return True
        try:
            quit_now = window.create_confirmation_dialog(
                "关闭闲鱼超级管家",
                "请选择关闭方式：\n\n"
                "【确定】完全退出 —— 停止自动回复、自动发货等全部后台服务\n\n"
                "【取消】最小化到任务栏 —— 后台继续挂机运行，"
                "之后可在任务栏托盘图标上右键选择「打开主界面」或「退出运行」",
            )
        except Exception:
            quit_now = False
        if quit_now:
            # 完全退出
            _QUIT_AFTER_CLOSE["quit"] = True
            _start_watchdog()
            _stop_backend_async()
            return True
        # 最小化到任务栏：阻止窗口关闭，隐藏窗口并显示托盘图标
        ensure_tray()
        threading.Thread(target=_safe_hide, daemon=True).start()
        return False

    window.events.closing += on_closing

    def on_loaded(window) -> None:
        """页面加载完成的诊断日志（便于排查）。"""
        try:
            url = window.get_current_url()
            title = window.evaluate_js("document.title")
            log(f"PAGE_LOADED url={url!r} title={title!r}")
        except Exception as e:
            log(f"PAGE_LOADED eval failed: {e}")

    window.events.loaded += on_loaded

    def boot() -> None:
        """后台线程：确保服务就绪后加载管理界面。"""
        try:
            if health_ok():
                log("检测到服务已在运行，直接进入管理界面")
                window.load_url(APP_URL)
                return
            log("未检测到服务，正在启动后端…")
            if not start_backend():
                window.load_html(error_html("无法启动本地服务程序。请确认 xianyu-butler.exe 与本程序在同一目录。"))
                return
            if wait_ready():
                log("服务已就绪，进入管理界面")
                window.load_url(APP_URL)
            else:
                log("等待服务超时")
                window.load_html(error_html(
                    "等待本地服务响应超时（240 秒）。<br>"
                    "可能原因：8080 端口被其他程序占用，或首次初始化耗时过长。"
                ))
        except Exception as e:
            log(f"启动流程异常: {e}")
            try:
                window.load_html(error_html(f"发生异常：{e}"))
            except Exception:
                pass

    threading.Thread(target=boot, daemon=True).start()

    if _SMOKE:
        def smoke() -> None:
            time.sleep(float(os.environ.get("GUI_SMOKE_TEST", "20")))
            try:
                url = window.get_current_url()
            except Exception as e:
                url = f"<err:{e}>"
            log(f"SMOKE url={url!r} health_ok={health_ok()} close_mode={_SMOKE_CLOSE}")
            # 模拟用户点击窗口右上角 X（WM_CLOSE），走真实关闭流程
            try:
                import ctypes
                hwnd = ctypes.windll.user32.FindWindowW(None, APP_TITLE)
                log(f"SMOKE hwnd={hwnd}")
                if hwnd:
                    ctypes.windll.user32.PostMessageW(hwnd, 0x0010, 0, 0)  # WM_CLOSE
                else:
                    window.destroy()
            except Exception as e:
                log(f"SMOKE close failed: {e}")

            if _SMOKE_CLOSE == "tray":
                # 托盘模式：验证隐藏 + 托盘图标 + 打开主界面(异步) + 托盘退出
                time.sleep(6)
                log(f"SMOKE tray_icon_created={_TRAY['icon'] is not None}")
                log("SMOKE 模拟托盘菜单：打开主界面（异步发起）")
                open_main_window()
                time.sleep(4)
                log("SMOKE 模拟托盘菜单：退出运行")
                tray_quit(_TRAY["icon"])
                # 兜底：无论如何退出
                time.sleep(25)
                os._exit(0)
        threading.Thread(target=smoke, daemon=True).start()

    try:
        webview.start(
            gui="edgechromium",
            private_mode=False,
            storage_path=storage_dir(),
        )
    except Exception as e:
        log(f"窗口启动失败: {e}")
        show_error_box(
            APP_TITLE,
            "无法创建应用窗口。\n\n"
            "本程序需要「Microsoft Edge WebView2 Runtime」组件（绝大多数 Windows 10/11 已自带）。\n"
            "如提示缺失，请安装后再试：\n"
            "https://developer.microsoft.com/microsoft-edge/webview2/",
        )
        return 1

    # 窗口关闭流程结束（完全退出 或 托盘退出）：等停止后端完成，再退出进程
    if _QUIT_AFTER_CLOSE["quit"]:
        _STOP_DONE.wait(timeout=15)
    log("界面已关闭")
    return 0


if __name__ == "__main__":
    sys.exit(main())
