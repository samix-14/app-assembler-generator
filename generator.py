import json
import os
import re
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from urllib.parse import urlparse

TITLE = "App Assembler Generator"
ROOT = os.path.dirname(os.path.abspath(__file__))

FEATURES = [
    ("list", "Elencare file e cartelle"),
    ("search", "Cercare file per nome"),
    ("open", "Aprire file e cartelle"),
    ("copy", "Copiare file e cartelle"),
    ("rename", "Rinominare file e cartelle"),
    ("delete", "Eliminare con conferma"),
    ("create", "Creare cartelle"),
    ("backup", "Backup e ripristino"),
    ("versions", "Confrontare versioni installate"),
    ("logs", "Cronologia operazioni"),
]


def safe_name(value):
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip()).strip(".-_")
    return cleaned or "nuova-app"


def parse_repo(value):
    parsed = urlparse(value.strip().rstrip("/"))
    if parsed.scheme not in ("https", "http") or parsed.netloc.lower() not in ("github.com", "www.github.com"):
        raise ValueError("Inserisci un URL GitHub pubblico, ad esempio https://github.com/utente/repository")
    parts = [p for p in parsed.path.split("/") if p]
    if len(parts) < 2:
        raise ValueError("L'URL deve contenere proprietario e nome della repository.")
    owner, repository = parts[0], parts[1].removesuffix(".git")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", owner) or not re.fullmatch(r"[A-Za-z0-9_.-]+", repository):
        raise ValueError("Il proprietario o il nome della repository non è valido.")
    return owner, repository


class Generator(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(TITLE)
        self.geometry("900x790")
        self.minsize(780, 680)
        self.configure(padx=16, pady=14)
        self.name = tk.StringVar()
        self.repo = tk.StringVar()
        self.parent = tk.StringVar(value=os.path.join(os.path.expanduser("~"), "Desktop"))
        self.main_file = tk.StringVar(value="index.html")
        self.mode = tk.StringVar(value="file")
        self.command = tk.StringVar(value="python -m http.server 8000")
        self.server_url = tk.StringVar(value="http://localhost:8000")
        self.server_dir = tk.StringVar(value=".")
        self.default_branch = tk.StringVar()
        self.enable_manager = tk.BooleanVar(value=True)
        self.feature_vars = {key: tk.BooleanVar(value=key in {"list", "search", "open", "copy", "rename", "backup"}) for key, _ in FEATURES}
        self.custom_commands = tk.StringVar()
        self.make_readme = tk.BooleanVar(value=True)
        self._build()

    def _build(self):
        ttk.Label(self, text=TITLE, font=("Segoe UI", 21, "bold")).pack(anchor="w")
        ttk.Label(self, text="Configura un bot da terminale per una repository GitHub pubblica.", foreground="#555").pack(anchor="w", pady=(2, 12))
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True)

        general = ttk.Frame(notebook, padding=14)
        launch = ttk.Frame(notebook, padding=14)
        manager = ttk.Frame(notebook, padding=14)
        notebook.add(general, text="1 · App e repository")
        notebook.add(launch, text="2 · Avvio")
        notebook.add(manager, text="3 · Gestione file")

        general.columnconfigure(1, weight=1)
        self._entry(general, 0, "Nome app", self.name, "es. meta-search")
        self._entry(general, 1, "Repository GitHub", self.repo, "https://github.com/utente/repository")
        ttk.Label(general, text="Cartella destinazione").grid(row=2, column=0, sticky="w", pady=9)
        ttk.Entry(general, textvariable=self.parent).grid(row=2, column=1, sticky="ew", padx=10, pady=9)
        ttk.Button(general, text="Sfoglia…", command=self._choose_parent).grid(row=2, column=2, pady=9)
        self._entry(general, 3, "Branch predefinito", self.default_branch, "facoltativo, es. 0.1")
        ttk.Checkbutton(general, text="Crea un file LEGGIMI.txt con le istruzioni", variable=self.make_readme).grid(row=4, column=1, sticky="w", padx=10, pady=10)
        ttk.Label(general, text="Le versioni vengono scaricate dai branch effettivamente presenti su GitHub. Il generatore non crea branch al posto tuo.", wraplength=700, foreground="#555").grid(row=5, column=0, columnspan=3, sticky="w", pady=(18, 0))

        launch.columnconfigure(1, weight=1)
        ttk.Label(launch, text="Comportamento quando avvii una versione", font=("Segoe UI", 12, "bold")).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 10))
        for row, (label, value, desc) in enumerate([
            ("Apri file", "file", "Apre il file principale con il programma predefinito di Windows."),
            ("Server locale", "server", "Avvia un comando nella cartella del progetto e apre l'URL locale."),
            ("Entrambi", "both", "Apre il file e avvia anche il server."),
        ], start=1):
            ttk.Radiobutton(launch, text=label, variable=self.mode, value=value).grid(row=row, column=0, sticky="w", pady=5)
            ttk.Label(launch, text=desc, foreground="#555", wraplength=520).grid(row=row, column=1, sticky="w", padx=12)
        ttk.Separator(launch).grid(row=4, column=0, columnspan=3, sticky="ew", pady=16)
        self._entry(launch, 5, "File principale", self.main_file, "es. index.html o src/index.html")
        self._entry(launch, 6, "Comando server", self.command, "es. python -m http.server 8000")
        self._entry(launch, 7, "URL server", self.server_url, "http://localhost:8000")
        self._entry(launch, 8, "Cartella server relativa", self.server_dir, ".")
        ttk.Label(launch, text="Esegui soltanto comandi che riconosci e di cui ti fidi.", foreground="#8a4b00").grid(row=9, column=1, sticky="w", padx=10, pady=(12, 0))

        ttk.Checkbutton(manager, text="Includi la modalità gestione file nel bot da terminale", variable=self.enable_manager, command=self._toggle_features).pack(anchor="w", pady=(0, 10))
        self.feature_frame = ttk.LabelFrame(manager, text="Funzioni da includere", padding=10)
        self.feature_frame.pack(fill="x")
        for i, (key, label) in enumerate(FEATURES):
            ttk.Checkbutton(self.feature_frame, text=label, variable=self.feature_vars[key]).grid(row=i // 2, column=i % 2, sticky="w", padx=8, pady=5)
        ttk.Label(manager, text="Comandi personalizzati (uno per riga)", font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(16, 4))
        ttk.Label(manager, text="Formato: nome | descrizione | comando. Esempio: test | Avvia i test | python -m unittest", foreground="#555").pack(anchor="w")
        self.custom_box = tk.Text(manager, height=5, wrap="word")
        self.custom_box.pack(fill="x", pady=(5, 0))
        self._toggle_features()

        footer = ttk.Frame(self)
        footer.pack(fill="x", pady=(14, 0))
        self.status = tk.StringVar(value="Pronto. Compila le sezioni e crea il bot.")
        ttk.Label(footer, textvariable=self.status, foreground="#555").pack(side="left", fill="x", expand=True)
        ttk.Button(footer, text="Crea assemblatore", command=self._create).pack(side="right")
        ttk.Button(footer, text="Esci", command=self.destroy).pack(side="right", padx=8)

    @staticmethod
    def _entry(parent, row, label, variable, hint):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=9)
        ttk.Entry(parent, textvariable=variable).grid(row=row, column=1, columnspan=2, sticky="ew", padx=10, pady=9)

    def _choose_parent(self):
        selected = filedialog.askdirectory(title="Scegli la cartella in cui creare il bot")
        if selected:
            self.parent.set(selected)

    def _toggle_features(self):
        state = "normal" if self.enable_manager.get() else "disabled"
        for child in self.feature_frame.winfo_children():
            try:
                child.configure(state=state)
            except tk.TclError:
                pass
        self.custom_box.configure(state=state)

    def _create(self):
        try:
            app_name = self.name.get().strip()
            if not app_name:
                raise ValueError("Inserisci il nome dell'app.")
            parent = self.parent.get().strip()
            if not parent or not os.path.isdir(parent):
                raise ValueError("Scegli una cartella destinazione già esistente.")
            owner, repository = parse_repo(self.repo.get())
            main_file = self.main_file.get().strip() or "index.html"
            if os.path.isabs(main_file) or ".." in main_file.replace("\\", "/").split("/"):
                raise ValueError("Il file principale deve essere un percorso relativo alla versione.")
            server_dir = self.server_dir.get().strip() or "."
            if os.path.isabs(server_dir) or ".." in server_dir.replace("\\", "/").split("/"):
                raise ValueError("La cartella server deve essere relativa e restare dentro la versione.")
            custom = []
            for number, line in enumerate(self.custom_box.get("1.0", "end").splitlines(), start=1):
                if not line.strip():
                    continue
                parts = [part.strip() for part in line.split("|", 2)]
                if len(parts) != 3 or not all(parts):
                    raise ValueError(f"Comando personalizzato alla riga {number}: usa nome | descrizione | comando.")
                custom.append({"name": parts[0], "description": parts[1], "command": parts[2]})

            root = os.path.join(parent, safe_name(app_name))
            if os.path.exists(root) and os.listdir(root):
                if not messagebox.askyesno("Cartella non vuota", f"La cartella contiene già file:\\n{root}\\n\\nContinuare senza cancellarli?"):
                    return
            bot_dir = os.path.join(root, "bot")
            folders = ["versioni_0.x", "versione_1.0", "versioni_1.1_plus", "versioni_altre", "backup"]
            for folder in [bot_dir] + [os.path.join(root, item) for item in folders]:
                os.makedirs(folder, exist_ok=True)

            template = os.path.join(ROOT, "assembler_template", "assembler.py")
            if not os.path.isfile(template):
                raise FileNotFoundError("Manca assembler_template/assembler.py. Riscarica tutta la repository, non soltanto generator.py.")
            with open(template, "r", encoding="utf-8") as stream:
                code = stream.read()
            config = {
                "app_name": app_name,
                "owner": owner,
                "repository": repository,
                "repository_url": f"https://github.com/{owner}/{repository}",
                "main_file": main_file,
                "start_mode": self.mode.get(),
                "server_command": self.command.get().strip(),
                "server_url": self.server_url.get().strip(),
                "server_directory": server_dir,
                "default_branch": self.default_branch.get().strip(),
                "enable_file_manager": self.enable_manager.get(),
                "file_manager_features": [key for key, _ in FEATURES if self.feature_vars[key].get()] if self.enable_manager.get() else [],
                "custom_commands": custom,
                "backup_text_files_only": True,
            }
            with open(os.path.join(bot_dir, "assembler.py"), "w", encoding="utf-8") as stream:
                stream.write(code)
            with open(os.path.join(bot_dir, "config.json"), "w", encoding="utf-8") as stream:
                json.dump(config, stream, indent=2, ensure_ascii=False)
            with open(os.path.join(bot_dir, "avvia_assemblatore.bat"), "w", encoding="utf-8", newline="") as stream:
                stream.write('@echo off\r\ncd /d "%~dp0"\r\npy assembler.py\r\nif errorlevel 1 python assembler.py\r\nif errorlevel 1 pause\r\n')
            if self.make_readme.get():
                content = f"""ASSEMBLATORE: {app_name}

Avvio:
1. Apri bot\\\\avvia_assemblatore.bat.
2. Scegli una versione/branch presente su GitHub e scaricala.
3. Usa le opzioni del menu per avviare la versione o gestire i file.

Cartelle versioni: {", ".join(folders[:-1])}, versioni_altre.
I backup dei file testuali sono in backup\\\\ e hanno estensione .txt.
I file originali conservano nome ed estensione.

Repository: https://github.com/{owner}/{repository}

Esegui soltanto codice e comandi che riconosci e di cui ti fidi.
"""
                with open(os.path.join(root, "LEGGIMI.txt"), "w", encoding="utf-8") as stream:
                    stream.write(content)
            self.status.set(f"Creato: {root}")
            if messagebox.askyesno("Assemblatore creato", f"Bot creato in:\\n{root}\\n\\nVuoi aprire la cartella?"):
                os.startfile(root)
        except Exception as error:
            messagebox.showerror("Creazione non riuscita", str(error))


if __name__ == "__main__":
    Generator().mainloop()
