import eel
import os
import sys
import subprocess
import threading
import time
import json
import ctypes
from ctypes import wintypes
import urllib.request
import re
import tkinter as tk
from tkinter import filedialog
from concurrent.futures import ThreadPoolExecutor
import pystray
from PIL import Image
import base64
import traceback # Добавлено для отлова критических ошибок

eel.init('web')

# Фикс путей для сборки PyInstaller
def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

if getattr(sys, 'frozen', False):
    ROOT_DIR = os.path.dirname(sys.executable)
    exe_path = sys.executable
else:
    ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
    exe_path = sys.executable + f' "{os.path.abspath(__file__)}"'
    
CONFIG_FILE = os.path.join(ROOT_DIR, "config.json")

def load_config():
    default_config = {
        "last_bat": "", "autostart": False, "start_minimized": False, "zapret_path": "", "bg_image": "",
        "theme": "amoled", "custom_color": "#ff0000", "custom_bg_color": "#050505",
        "custom_text_color": "#ffffff", "custom_muted_color": "#aaaaaa",
        "custom_alpha": "0.6", "custom_blur": "20", "logs_hidden": False,
        "transparent_frame": True, "frame_color": "#050505", "tray_color": "#9b59b6" 
    }
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f: 
                default_config.update(json.load(f))
        except: pass
    return default_config

def save_config(data):
    # Атомарное сохранение конфига через временный файл
    temp_file = CONFIG_FILE + ".tmp"
    try:
        with open(temp_file, "w", encoding="utf-8") as f: 
            json.dump(data, f, indent=4)
        os.replace(temp_file, CONFIG_FILE)
    except Exception as e: 
        pass

config_data = load_config()
if config_data.get("zapret_path") and os.path.exists(config_data["zapret_path"]):
    ZAPRET_DIR = config_data["zapret_path"]
else:
    ZAPRET_DIR = os.path.join(ROOT_DIR, "zapret")

is_ws_active = None
is_service_installed = None
# Оптимизация пулов потоков 
executor = ThreadPoolExecutor(max_workers=3) 

def is_admin():
    try: return ctypes.windll.shell32.IsUserAnAdmin()
    except: return False

def get_silent_info():
    si = subprocess.STARTUPINFO()
    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    si.wShowWindow = subprocess.SW_HIDE
    return si

CREATE_NO_WINDOW = 0x08000000

def log_to_web(msg):
    try: eel.add_log(msg)
    except: pass

def create_ninja_bat(bat_name):
    bat_path = os.path.join(ZAPRET_DIR, bat_name)
    temp_bat_path = os.path.join(ZAPRET_DIR, "temp_ui_run.bat")
    try:
        with open(bat_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        with open(temp_bat_path, 'w', encoding='utf-8') as f:
            for line in lines:
                if "winws" in line.lower() and "start" in line.lower():
                    line = re.sub(r'(?i)start\s+(?:"[^"]*"\s*)?(?:/(?:min|b|wait)\s*)?', '', line)
                # Фильтр блокировки редиректов на GitHub
                if "start http" in line.lower(): 
                    continue
                f.write(line)
        return True
    except Exception as e:
        return False

@eel.expose
def pick_bg_image():
    root = tk.Tk()
    root.attributes("-topmost", True)
    root.withdraw()
    file_path = filedialog.askopenfilename(title="Выберите фон", filetypes=[("Изображения", "*.png *.jpg *.jpeg *.webp")])
    root.destroy()
    if file_path:
        config = load_config()
        config['bg_image'] = file_path
        save_config(config)
        return True
    return False

@eel.expose
def get_bg_image_base64():
    config = load_config()
    path = config.get('bg_image', '')
    if path and os.path.exists(path):
        try:
            with open(path, "rb") as f:
                encoded = base64.b64encode(f.read()).decode('utf-8')
                ext = path.split('.')[-1].lower()
                mime = f"image/{ext}" if ext != 'jpg' else "image/jpeg"
                return f"data:{mime};base64,{encoded}"
        except: pass
    return ""

@eel.expose
def clear_bg_image():
    config = load_config()
    config['bg_image'] = ""
    save_config(config)

@eel.expose
def get_settings(): return load_config()

@eel.expose
def save_settings(new_config):
    config = load_config()
    config.update(new_config)
    save_config(config)
    # Замена блокируемого реестра на Планировщик задач (Schtasks)
    try:
        if config.get("autostart"):
            cmd = f'schtasks /create /tn "ZapretUI" /tr "\'{exe_path}\'" /sc onlogon /rl highest /f'
            subprocess.run(cmd, startupinfo=get_silent_info(), creationflags=CREATE_NO_WINDOW)
        else:
            subprocess.run('schtasks /delete /tn "ZapretUI" /f', startupinfo=get_silent_info(), creationflags=CREATE_NO_WINDOW)
    except Exception as e:
        log_to_web(f"Ошибка изменения автозапуска: {e}")

@eel.expose
def pick_folder():
    root = tk.Tk()
    root.attributes("-topmost", True)
    root.withdraw()
    folder_path = filedialog.askdirectory(title="Выберите папку с файлами zapret")
    root.destroy()
    return folder_path

@eel.expose
def update_zapret_path(new_path):
    global ZAPRET_DIR
    if os.path.exists(new_path):
        ZAPRET_DIR = new_path
        config = load_config()
        config["zapret_path"] = new_path
        save_config(config)
        return True
    return False

@eel.expose
def reset_zapret_path():
    global ZAPRET_DIR
    ZAPRET_DIR = os.path.join(ROOT_DIR, "zapret")
    config = load_config()
    config["zapret_path"] = ""
    save_config(config)
    return True

@eel.expose
def save_last_bat(bat_name):
    config = load_config()
    config["last_bat"] = bat_name
    save_config(config)

@eel.expose
def get_last_bat(): return load_config().get("last_bat", "")

@eel.expose
def get_bat_files():
    if not os.path.exists(ZAPRET_DIR): return ["Ошибка: Папка zapret не найдена!"]
    exclude = ['service_install.bat', 'service_remove.bat', 'blockcheck.bat', 'preset_russia.bat', 'service.bat', 'service_goodbyedpi.bat', 'temp_ui_run.bat']
    bats = [f for f in os.listdir(ZAPRET_DIR) if f.endswith('.bat') and f not in exclude]
    return bats if bats else ["Батники не найдены"]

DWMWA_CAPTION_COLOR = 35
DWMWA_USE_IMMERSIVE_DARK_MODE = 20
DWMWA_SYSTEMBACKDROP_TYPE = 38

@eel.expose
def change_frame_color(hex_color):
    try:
        hex_color = hex_color.lstrip('#')
        r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        color = ctypes.c_int(r | (g << 8) | (b << 16))
        win_build = sys.getwindowsversion().build
        
        def enum_cb(h, lparam):
            if ctypes.windll.user32.IsWindowVisible(h):
                length = ctypes.windll.user32.GetWindowTextLengthW(h)
                if length > 0:
                    title_buff = ctypes.create_unicode_buffer(length + 1)
                    ctypes.windll.user32.GetWindowTextW(h, title_buff, length + 1)
                    class_buff = ctypes.create_unicode_buffer(256)
                    ctypes.windll.user32.GetClassNameW(h, class_buff, 256)
                    
                    if "Zapret UI" in title_buff.value and class_buff.value == "Chrome_WidgetWin_1":
                        if win_build >= 22000:
                            ctypes.windll.dwmapi.DwmSetWindowAttribute(h, DWMWA_CAPTION_COLOR, ctypes.byref(color), ctypes.sizeof(color))
                            backdrop = ctypes.c_int(2) 
                            ctypes.windll.dwmapi.DwmSetWindowAttribute(h, DWMWA_SYSTEMBACKDROP_TYPE, ctypes.byref(backdrop), ctypes.sizeof(backdrop))
                        elif win_build >= 17763:
                            dark_mode = ctypes.c_int(1 if (r+g+b)/3 < 128 else 0)
                            ctypes.windll.dwmapi.DwmSetWindowAttribute(h, DWMWA_USE_IMMERSIVE_DARK_MODE, ctypes.byref(dark_mode), ctypes.sizeof(dark_mode))
                        return False
            return True
        
        def apply():
            time.sleep(1.5) # РЕШЕНИЕ: Увеличен таймаут для Win11, чтобы окно успело создаться
            ctypes.windll.user32.EnumWindows(ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)(enum_cb), 0)
        
        threading.Thread(target=apply, daemon=True).start()
    except Exception:
        pass

@eel.expose
def change_tray_icon(hex_color):
    global icon 
    try:
        hex_color = hex_color.lstrip('#')
        r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        
        base_path = resource_path("web/icon.png")
        if not os.path.exists(base_path): return
            
        base_img = Image.open(base_path).convert("RGBA")
        
        extrema = base_img.getextrema()
        if extrema[3][0] < 255: 
            mask = base_img.split()[3]
        else: 
            gray = base_img.convert("L")
            mask = gray.point(lambda p: 255 - p if p < 128 else 0)
        
        colored_img = Image.new("RGBA", base_img.size, (r, g, b, 255))
        colored_img.putalpha(mask)
        
        icon.icon = colored_img
    except Exception as e:
        pass
        
@eel.expose
def toggle_engine(bat_name):
    global is_ws_active
    if is_ws_active != True:
        if "..." in bat_name: return
        if create_ninja_bat(bat_name):
            cmd = f'cmd /c "temp_ui_run.bat"'
            subprocess.Popen(cmd, cwd=ZAPRET_DIR, startupinfo=get_silent_info(), creationflags=CREATE_NO_WINDOW)
            log_to_web(f"Запуск обхода: {bat_name}")
    else:
        subprocess.Popen('taskkill /F /IM winws.exe /T', startupinfo=get_silent_info(), creationflags=CREATE_NO_WINDOW)
        if os.path.exists(os.path.join(ZAPRET_DIR, "service_remove.bat")):
            subprocess.Popen('cmd /c "service_remove.bat"', cwd=ZAPRET_DIR, startupinfo=get_silent_info(), creationflags=CREATE_NO_WINDOW)
        log_to_web("Обход остановлен.")

@eel.expose
def get_status(): return is_ws_active

def bg_monitor():
    global is_ws_active, is_service_installed
    time.sleep(1) 
    while True:
        try:
            out_ws = subprocess.check_output('tasklist /FI "IMAGENAME eq winws.exe"', startupinfo=get_silent_info(), creationflags=CREATE_NO_WINDOW).decode('cp866', errors='ignore')
            current_ws = "winws.exe" in out_ws
        except: current_ws = False
            
        if current_ws != is_ws_active:
            is_ws_active = current_ws
            try: eel.update_status(is_ws_active)
            except: pass
        
        try:
            out_svc = subprocess.check_output('sc query zapret', startupinfo=get_silent_info(), creationflags=CREATE_NO_WINDOW).decode('cp866', errors='ignore')
            current_svc = "SERVICE_NAME: zapret" in out_svc
        except: current_svc = False
            
        if current_svc != is_service_installed:
            is_service_installed = current_svc
            try: eel.update_service_status(is_service_installed)
            except: pass
            
        time.sleep(1.5)

@eel.expose
def open_service_bat():
    if os.path.exists(os.path.join(ZAPRET_DIR, "service.bat")):
        subprocess.Popen('start cmd /c "service.bat"', shell=True, cwd=ZAPRET_DIR)
        log_to_web("Открыто меню service.bat.")
    else: 
        log_to_web("ОШИБКА: Файл service.bat не найден!")

@eel.expose
def start_diagnostics():
    threading.Thread(target=_net_logic, daemon=True).start()

def _net_logic():
    def check_url(url):
        try:
            urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'}), timeout=2)
            return True
        except: return False
    
    def ping_host(host):
        try:
            out = subprocess.check_output(f"ping -n 1 -w 1000 {host}", startupinfo=get_silent_info(), creationflags=CREATE_NO_WINDOW).decode('cp866')
            match = re.search(r'[=<](\d+)\s*(?:ms|мс)', out.lower())
            return int(match.group(1)) if match else None
        except: return None

    future_ds = executor.submit(check_url, "https://discord.com")
    future_yt = executor.submit(check_url, "https://www.youtube.com")
    pings = [r for r in list(executor.map(ping_host, ["8.8.8.8", "1.1.1.1", "google.com"])) if r is not None]
    
    ds, yt = future_ds.result(), future_yt.result()
    avg_ping = (sum(pings) // len(pings)) if pings else "ОШИБКА"
    
    eel.update_diagnostics(ds, yt, avg_ping)
    log_to_web("Диагностика сети завершена.")

@eel.expose
def start_scanner():
    global is_service_installed
    if is_service_installed:
        eel.tuner_print("ОШИБКА: Удалите системную службу перед сканированием!")
        eel.scanner_finished("")
        return
    threading.Thread(target=_scanner_logic, daemon=True).start()

def _scanner_logic():
    subprocess.call('taskkill /F /IM winws.exe /T', startupinfo=get_silent_info(), creationflags=CREATE_NO_WINDOW)
    time.sleep(1)
    bats = get_bat_files()
    if not bats or "Ошибка" in bats[0]:
        eel.tuner_print("Батники не найдены.")
        eel.scanner_finished("")
        return
    results = []
    def check_access(url):
        try:
            urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'}), timeout=3)
            return True
        except: return False
    def get_ping():
        try:
            out = subprocess.check_output("ping -n 1 -w 1000 8.8.8.8", startupinfo=get_silent_info(), creationflags=CREATE_NO_WINDOW).decode('cp866')
            m = re.search(r'[=<](\d+)\s*(?:ms|мс)', out.lower())
            return int(m.group(1)) if m else 999
        except: return 999

    for bat in bats:
        eel.tuner_print(f"Тестирую: {bat}")
        if create_ninja_bat(bat):
            subprocess.Popen(f'cmd /c "temp_ui_run.bat"', cwd=ZAPRET_DIR, startupinfo=get_silent_info(), creationflags=CREATE_NO_WINDOW)
        else:
            subprocess.Popen(f'cmd /c "{bat}"', cwd=ZAPRET_DIR, startupinfo=get_silent_info(), creationflags=CREATE_NO_WINDOW)
            
        time.sleep(3)
        ds, yt, ping = check_access("https://discord.com"), check_access("https://www.youtube.com"), get_ping()
        eel.tuner_print(f" -> ДС: {'OK' if ds else 'FAIL'} | Ютуб: {'OK' if yt else 'FAIL'} | Пинг: {ping}мс")
        results.append({'bat': bat, 'ds': ds, 'yt': yt, 'ping': ping})
        subprocess.call('taskkill /F /IM winws.exe /T', startupinfo=get_silent_info(), creationflags=CREATE_NO_WINDOW)
        time.sleep(1)

    eel.tuner_print("---------------------------")
    valid = [r for r in results if r['ds'] and r['yt']]
    best_bat = ""
    if valid:
        valid.sort(key=lambda x: x['ping'])
        winner = valid[0]
        eel.tuner_print(f"ЛУЧШИЙ КОНФИГ: {winner['bat']} ({winner['ping']}мс)")
        best_bat = winner['bat']
    else:
        eel.tuner_print("ВНИМАНИЕ: Нет конфига, который открывает оба сайта.")
    eel.scanner_finished(best_bat)
    log_to_web("Сканирование завершено.")

if __name__ == '__main__':
    if not is_admin():
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
        sys.exit()
    else:
        # Mutex для защиты от двойного запуска 
        mutex = ctypes.windll.kernel32.CreateMutexW(None, False, "ZapretUI_Mutex_sttc")
        if ctypes.windll.kernel32.GetLastError() == 183: # ERROR_ALREADY_EXISTS
            ctypes.windll.user32.MessageBoxW(0, "Программа уже запущена!\nПроверьте системный трей.", "Zapret UI", 0x30)
            sys.exit()

        threading.Thread(target=bg_monitor, daemon=True).start()
        
        def create_tray_image():
            base_path = resource_path("web/icon.png")
            if os.path.exists(base_path):
                try:
                    base_img = Image.open(base_path).convert("RGBA")
                    config = load_config()
                    hex_color = config.get("tray_color", "#9b59b6").lstrip('#')
                    r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
                    
                    extrema = base_img.getextrema()
                    if extrema[3][0] < 255:
                        mask = base_img.split()[3]
                    else:
                        gray = base_img.convert("L")
                        mask = gray.point(lambda p: 255 - p if p < 128 else 0)
                        
                    colored = Image.new("RGBA", base_img.size, (r, g, b, 255)) 
                    colored.putalpha(mask)
                    return colored
                except: pass
            return Image.new('RGBA', (64, 64), (0, 0, 0, 0))

        def show_window(icon, item):
            try: eel.show('index.html')
            except: pass

        def quit_app(icon, item):
            icon.stop()
            subprocess.Popen('taskkill /F /IM winws.exe /T', startupinfo=get_silent_info(), creationflags=CREATE_NO_WINDOW)
            os._exit(0)

        img = create_tray_image()
        icon = pystray.Icon("ZapretUI", img, "Zapret UI", menu=pystray.Menu(
            pystray.MenuItem('Открыть интерфейс', show_window, default=True),
            pystray.MenuItem('Выход', quit_app)
        ))
        threading.Thread(target=icon.run, daemon=True).start()

        def on_close(page, sockets):
            current_config = load_config()
            if not current_config.get("start_minimized", False):
                icon.stop()
                subprocess.Popen('taskkill /F /IM winws.exe /T', startupinfo=get_silent_info(), creationflags=CREATE_NO_WINDOW)
                os._exit(0)

        # Флаг enable-transparent-visuals нужен для прозрачной рамки
        app_args = ['--window-size=480,890', '--enable-transparent-visuals']
        
        # Глобальный отлов ошибок UI 
        try:
            try:
                eel.start('index.html', size=(480, 890), port=0, block=False, close_callback=on_close, cmdline_args=app_args)
            except Exception:
                eel.start('index.html', size=(480, 890), port=0, mode='edge', block=False, close_callback=on_close, cmdline_args=app_args)

            while True:
                eel.sleep(1)
        except Exception as e:
            error_msg = traceback.format_exc()
            ctypes.windll.user32.MessageBoxW(0, f"Критическая ошибка отрисовки UI:\n{error_msg}\n\nВозможно, в Windows поврежден WebView2 или Edge.", "Zapret UI Crash", 0x10)
            sys.exit(1)
