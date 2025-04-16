import os
import sys
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import json
import ctypes

CHECK_INSTALL = 'install_key.json'

def read_check_file(file: str) -> dict:
    with open(file, 'r') as checkfile:
        data = json.load(checkfile)
    return data

def set_check_file(file: str) -> None:
    data_dict: dict = {'installed': 'true'}
    with open(file, 'w') as checkfile:
        json.dump(data_dict, checkfile)

class InstallerGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("WashTradePVP Setup")
        self.root.geometry("500x300")
        self.root.resizable(False, False)
        
        self.create_widgets()
        
        self.installation_complete = False
        
        self.root.after(1000, self.start_installation)
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.mainloop()

    def create_widgets(self):
        ttk.Label(
            self.root,
            text="WashTradePVP Installer",
            font=('Helvetica', 16, 'bold')
        ).pack(pady=20)

        self.progress = ttk.Progressbar(
            self.root,
            length=400,
            mode='determinate'
        )
        self.progress.pack(pady=20)

        self.status_label = ttk.Label(
            self.root,
            text="Подготовка к установке...",
            font=('Helvetica', 10)
        )
        self.status_label.pack(pady=10)

    def update_status(self, text, progress):
        self.status_label.config(text=text)
        self.progress['value'] = progress
        self.root.update()

    def start_installation(self):
        threading.Thread(target=self.install_process, daemon=True).start()

    def install_process(self):
        try:
            self.update_status("Установка необходимых компонентов...", 20)
            
            pip_process = subprocess.Popen(
                [sys.executable, "-m", "pip", "install", "telethon", "asyncio", "requests", "--quiet"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            stdout, stderr = pip_process.communicate()
            
            if pip_process.returncode != 0:
                raise Exception(f"Ошибка установки: {stderr.decode()}")

            self.update_status("Настройка компонентов...", 70)
            time.sleep(2)

            set_check_file(CHECK_INSTALL)

            self.update_status("Установка завершена успешно!", 100)
            self.installation_complete = True
            
            self.root.after(2000, self.cleanup_and_exit)

        except Exception as e:
            messagebox.showerror(
                "Ошибка установки",
                f"Произошла ошибка при установке:\n{str(e)}"
            )
            self.cleanup_and_exit()

    def cleanup_and_exit(self):
        self.root.quit()

    def on_closing(self):
        if not self.installation_complete:
            if messagebox.askokcancel("Прервать установку", 
                                    "Вы уверены, что хотите прервать установку?"):
                self.cleanup_and_exit()
        else:
            self.cleanup_and_exit()

def is_already_running():
    mutex = ctypes.windll.kernel32.CreateMutexW(None, 1, "WashTradePVP_Mutex")
    return ctypes.windll.kernel32.GetLastError() == 183  # ERROR_ALREADY_EXISTS

def main() -> None:
    if is_already_running():
        messagebox.showinfo("Информация", "Приложение уже запущено.")
        return

    if getattr(sys, 'frozen', False):
        # Запускаем основное приложение
        if read_check_file(CHECK_INSTALL)['installed'] == 'true':
            subprocess.Popen([sys.executable, "wash_trade_pvp_final_high.py"])
        else:
            InstallerGUI()
    else:
        # Если это обычный Python-скрипт
        if read_check_file(CHECK_INSTALL)['installed'] == 'true':
            os.startfile('wash_trade_pvp_final_high.exe')
        else:
            InstallerGUI()

if __name__ == "__main__":
    main()
