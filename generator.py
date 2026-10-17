import json
import os
import re
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from urllib.parse import urlparse

APP_TITLE = "App Assembler Generator"
ROOT = os.path.dirname(os.path.abspath(__file__))


def safe_name(value):
    value = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip())
    return value.strip(".-_") or "new-app"


def parse_repo(url):
    parsed = urlparse(url.strip().rstrip("/"))
    if parsed.netloc.lower() not in {"github.com", "www.github.com"}:
        raise ValueError("Inserisci un URL GitHub, per esempio https://github.com/utente/repository")
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) < 2:
        raise ValueError("L'URL deve contenere proprietario e repository.")
    return parts[0], parts[1].removesuffix(".git")


class Generator(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("760x650")
        self.minsize(680, 600)
        self.configure(padx=18, pady=16)
        self.name = tk.StringVar()
        self.repo = tk.StringVar()
        self.parent = tk.StringVar(value=os.path.join(os.path.expanduser("~"), "Desktop"))
        self.main_file = tk.StringVar(value="index.html")
        self.mode = tk.StringVar(value="file")
        self.command = tk.StringVar(value="python -m http.server 8000")
        self.server_url = tk.StringVar(value="http://localhost:8000")
        self.server_dir = tk.StringVar(value=".")
        self.default_branch = tk.StringVar()
        self.readme = tk.BooleanVar(value=True)
        self.build_ui()

    def build_ui(self):
        ttk.Label(self, text=APP_TITLE, font=("Segoe UI", 20, "bold")).pack(anchor="w")
        ttk.Label(self, text="Crea un assemblatore su misura per una repository GitHub pubblica.").pack(anchor="w", pady=(3, 16))
        form = ttk.Frame(self)
        form.pack(fill="x")
        form.columnconfigure(1, weight=1)
        self.field(form, 0, "Nome app", self.name, "es. meta-search")
        self.field(form, 1, "Repository GitHub", self.repo, "https://github.com/utente/repository")
        ttk.Label(form, text="Cartella destinazione").grid(row=2, column=0, sticky="w", pady=7)
        ttk.Entry(form, textvariable=self.parent).grid(row=2, column=1, sticky="ew", padx=(12, 8), pady=7)
        ttk.Button(form, text="Sfoglia…", command=self.choose_parent).grid(row=2, column=2, pady=7)
        self.field(form, 3, "File principale", self.main_file, "index.html")
        ttk.Label(form, text="Avvio").grid(row=4, column=0, sticky="w", pady=7)
        modes = ttk.Frame(form)
        modes.grid(row=4, column=1, columnspan=2, sticky="w", padx=(12, 0), pady=7)
        for label, value in (("Apri file", "file"), ("Server locale", "server"), ("Entrambi", "both")):
            ttk.Radiobutton(modes, text=label, variable=self.mode, value=value).pack(side="left", padx=(0, 12))
        self.field(form, 5, "Comando server", self.command, "python -m http.server 8000")
        self.field(form, 6, "URL server", self.server_url, "http://localhost:8000")
        self.field(form, 7, "Cartella server relativa", self.server_dir, ".")
        self.field(form, 8, "Branch predefinito", self.default_branch, "facoltativo, es. 0.1")
        ttk.Checkbutton(form, text="Crea anche LEGGIMI.txt", variable=self.readme).grid(row=9, column=1, sticky="w", padx=(12, 0), pady=8)
        ttk.Separator(self).pack(fill="x", pady=12)
        ttk.Label(self, text="Ogni assemblatore avrà il proprio bot, la configurazione, le cartelle delle versioni e i backup testuali.").pack(anchor="w")
        actions = ttk.Frame(self)
        actions.pack(fill="x", pady=(18, 0))
        ttk.Button(actions, text="Crea assemblatore", command=self.create_app).pack(side="left")
        ttk.Button(actions, text="Esci", command=self.destroy).pack(side="right")
        self.status = tk.StringVar(value="Pronto.")
        ttk.Label(self, textvariable=self.status, foreground="#555").pack(anchor="w", pady=(12, 0))

    @staticmethod
    def field(parent, row, label, variable, hint):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=7)
        ttk.Entry(parent, textvariable=variable).grid(row=row, column=1, columnspan=2, sticky="ew", padx=(12, 0), pady=7)

    def choose_parent(self):
        selected = filedialog.askdirectory(title="Scegli dove creare la cartella dell'app")
        if selected:
            self.parent.set(selected)

    def create_app(self):
        try:
            app_name = self.name.get().strip()
            if not app_name:
                raise ValueError("Inserisci il nome dell'app.")
            parent = self.parent.get().strip()
            if not parent or not os.path.isdir(parent):
                raise ValueError("Scegli una cartella destinazione esistente.")
            owner, repo = parse_repo(self.repo.get())
            app_root = os.path.join(parent, safe_name(app_name))
            if os.path.exists(app_root) and os.listdir(app_root):
                if not messagebox.askyesno("Cartella non vuota", f"La cartella esiste e contiene file:\n{app_root}\n\nContinuare senza cancellare i file esistenti?"):
                    return

            config = {
                "app_name": app_name,
                "owner": owner,
                "repository": repo,
                "repository_url": f"https://github.com/{owner}/{repo}",
                "main_file": self.main_file.get().strip() or "index.html",
                "start_mode": self.mode.get(),
                "server_command": self.command.get().strip(),
                "server_url": self.server_url.get().strip(),
                "server_directory": self.server_dir.get().strip() or ".",
                "default_branch": self.default_branch.get().strip(),
                "backup_text_files_only": True
            }
            bot = os.path.join(app_root, "bot")
            for folder in (bot, os.path.join(app_root, "versioni_0.x"),
                           os.path.join(app_root, "versione_1.0"),
                           os.path.join(app_root, "versioni_1.1_plus"),
                           os.path.join(app_root, "versioni_altre"),
                           os.path.join(app_root, "backup")):
                os.makedirs(folder, exist_ok=True)

            template = os.path.join(ROOT, "assembler_template", "assembler.py")
            if not os.path.isfile(template):
                raise FileNotFoundError("Manca assembler_template/assembler.py. Scarica tutti i file della repository.")
            with open(template, "r", encoding="utf-8") as source:
                assembler_code = source.read()
            with open(os.path.join(bot, "assembler.py"), "w", encoding="utf-8") as out:
                out.write(assembler_code)
            with open(os.path.join(bot, "config.json"), "w", encoding="utf-8") as out:
                json.dump(config, out, indent=2, ensure_ascii=False)
            with open(os.path.join(bot, "avvia_assemblatore.bat"), "w", encoding="utf-8", newline="") as out:
                out.write('@echo off\r\ncd /d "%~dp0"\r\npy assembler.py\r\nif errorlevel 1 python assembler.py\r\nif errorlevel 1 pause\r\n')
            if self.readme.get():
                readme = f"""ASSEMBLATORE: {app_name}

1. Apri bot\\avvia_assemblatore.bat.
2. Seleziona un branch e scarica la versione.
3. Le versioni vengono ordinate nelle cartelle versioni_0.x, versione_1.0, versioni_1.1_plus o versioni_altre.
4. I file testuali supportati vengono copiati in backup con estensione .txt.
5. Seleziona una versione scaricata e premi Avvia versione.

Repository: https://github.com/{owner}/{repo}

Scarica ed esegui solo codice di cui ti fidi.
"""
                with open(os.path.join(app_root, "LEGGIMI.txt"), "w", encoding="utf-8") as out:
                    out.write(readme)
            self.status.set(f"Creato: {app_root}")
            if messagebox.askyesno("Creato", f"Assemblatore creato in:\n{app_root}\n\nVuoi aprire la cartella?"):
                os.startfile(app_root)
        except Exception as exc:
            messagebox.showerror("Impossibile creare l'assemblatore", str(exc))


if __name__ == "__main__":
    Generator().mainloop()
