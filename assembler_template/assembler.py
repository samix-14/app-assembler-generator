import io
import json
import os
import re
import shutil
import subprocess
import threading
import urllib.request
import webbrowser
import zipfile
import tkinter as tk
from tkinter import ttk, messagebox

HERE = os.path.dirname(os.path.abspath(__file__))
APP_ROOT = os.path.dirname(HERE)
with open(os.path.join(HERE, "config.json"), encoding="utf-8") as handle:
    CONFIG = json.load(handle)

TEXT_EXTENSIONS = {
    ".html", ".htm", ".css", ".js", ".mjs", ".cjs", ".json", ".py", ".txt",
    ".md", ".xml", ".svg", ".yml", ".yaml", ".toml", ".ini", ".csv", ".ts",
    ".tsx", ".jsx", ".java", ".c", ".h", ".cpp", ".hpp", ".cs", ".php",
    ".rb", ".go", ".rs", ".sh", ".bat", ".ps1", ".sql"
}


def github_json(url):
    request = urllib.request.Request(url, headers={
        "User-Agent": "AppAssembler/0.1",
        "Accept": "application/vnd.github+json"
    })
    with urllib.request.urlopen(request, timeout=25) as response:
        return json.loads(response.read().decode("utf-8"))


def branches():
    url = f"https://api.github.com/repos/{CONFIG['owner']}/{CONFIG['repository']}/branches?per_page=100"
    return [item["name"] for item in github_json(url)]


def safe_branch(branch):
    return re.sub(r"[^A-Za-z0-9._-]+", "_", branch).strip("._") or "branch"


def version_category(branch):
    match = re.match(r"^v?(\d+)\.(\d+)(?:\.(\d+))?", branch.strip(), re.I)
    if not match:
        return "versioni_altre"
    major, minor = int(match.group(1)), int(match.group(2))
    if major == 0:
        return "versioni_0.x"
    if major == 1 and minor == 0:
        return "versione_1.0"
    if major > 1 or (major == 1 and minor >= 1):
        return "versioni_1.1_plus"
    return "versioni_altre"


def safe_extract_branch(branch):
    url = f"https://api.github.com/repos/{CONFIG['owner']}/{CONFIG['repository']}/zipball/{branch}"
    request = urllib.request.Request(url, headers={"User-Agent": "AppAssembler/0.1"})
    with urllib.request.urlopen(request, timeout=60) as response:
        archive_bytes = response.read()
    with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
        names = archive.namelist()
        if not names:
            raise RuntimeError("L'archivio scaricato è vuoto.")
        prefix = names[0].split("/", 1)[0] + "/"
        target = os.path.join(APP_ROOT, version_category(branch), safe_branch(branch))
        if os.path.exists(target):
            if not messagebox.askyesno("Versione già presente",
                f"La cartella esiste già:\n{target}\n\nSostituirla? I backup testuali verranno aggiornati."):
                return None
            make_backups(branch, target, suffix="precedente")
            shutil.rmtree(target)
        os.makedirs(target, exist_ok=True)
        for name in names:
            if not name.startswith(prefix):
                continue
            relative = name[len(prefix):]
            if not relative:
                continue
            normalized = os.path.normpath(relative)
            if normalized == ".." or normalized.startswith(".." + os.sep) or os.path.isabs(normalized):
                continue
            destination = os.path.join(target, normalized)
            if name.endswith("/"):
                os.makedirs(destination, exist_ok=True)
                continue
            os.makedirs(os.path.dirname(destination), exist_ok=True)
            with archive.open(name) as source, open(destination, "wb") as output:
                shutil.copyfileobj(source, output)
    make_backups(branch, target)
    return target


def make_backups(branch, source_dir, suffix=""):
    backup_root = os.path.join(APP_ROOT, "backup", safe_branch(branch))
    if suffix:
        backup_root = os.path.join(backup_root, suffix)
    for root, _, filenames in os.walk(source_dir):
        for filename in filenames:
            if os.path.splitext(filename)[1].lower() not in TEXT_EXTENSIONS:
                continue
            source = os.path.join(root, filename)
            relative = os.path.relpath(source, source_dir)
            destination = os.path.join(backup_root, relative + ".txt")
            os.makedirs(os.path.dirname(destination), exist_ok=True)
            shutil.copy2(source, destination)


def find_main(directory, configured):
    direct = os.path.join(directory, configured)
    if os.path.isfile(direct):
        return direct
    wanted = os.path.basename(configured).lower()
    for root, _, files in os.walk(directory):
        for filename in files:
            if filename.lower() == wanted:
                return os.path.join(root, filename)
    return None


class Assembler(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Assemblatore - " + CONFIG["app_name"])
        self.geometry("780x560")
        self.minsize(650, 450)
        self.branch_var = tk.StringVar()
        self.status = tk.StringVar(value="Pronto.")
        self.build_ui()
        self.after(200, self.refresh_branches)

    def build_ui(self):
        frame = ttk.Frame(self, padding=16)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text=CONFIG["app_name"], font=("Segoe UI", 19, "bold")).pack(anchor="w")
        ttk.Label(frame, text=CONFIG["repository_url"]).pack(anchor="w", pady=(2, 14))
        line = ttk.Frame(frame)
        line.pack(fill="x")
        ttk.Label(line, text="Branch").pack(side="left")
        self.branch_box = ttk.Combobox(line, textvariable=self.branch_var, state="readonly")
        self.branch_box.pack(side="left", fill="x", expand=True, padx=10)
        ttk.Button(line, text="Aggiorna elenco", command=self.refresh_branches).pack(side="left")
        buttons = ttk.Frame(frame)
        buttons.pack(fill="x", pady=14)
        ttk.Button(buttons, text="Scarica versione", command=self.download).pack(side="left")
        ttk.Button(buttons, text="Apri cartella app", command=lambda: os.startfile(APP_ROOT)).pack(side="left", padx=8)
        ttk.Button(buttons, text="Avvia versione", command=self.launch).pack(side="left")
        ttk.Label(frame, text="Attività", font=("Segoe UI", 11, "bold")).pack(anchor="w")
        self.log = tk.Text(frame, height=15, wrap="word", state="disabled")
        self.log.pack(fill="both", expand=True, pady=(5, 8))
        ttk.Label(frame, textvariable=self.status).pack(anchor="w")

    def log_line(self, message):
        self.log.configure(state="normal")
        self.log.insert("end", message + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")
        self.status.set(message)

    def report_error(self, title, error):
        self.after(0, lambda: messagebox.showerror(title, error))
        self.after(0, lambda: self.status.set("Operazione non riuscita."))

    def refresh_branches(self):
        self.status.set("Lettura dei branch GitHub…")
        def worker():
            try:
                values = branches()
                self.after(0, lambda: self.set_branches(values))
            except Exception as error:
                self.report_error("Errore GitHub", str(error))
        threading.Thread(target=worker, daemon=True).start()

    def set_branches(self, values):
        self.branch_box["values"] = values
        preferred = CONFIG.get("default_branch", "")
        if preferred in values:
            self.branch_var.set(preferred)
        elif values:
            self.branch_var.set(values[0])
        self.log_line(f"Branch trovati: {len(values)}")

    def download(self):
        branch = self.branch_var.get()
        if not branch:
            messagebox.showwarning("Nessun branch", "Aggiorna l'elenco e seleziona un branch.")
            return
        self.status.set(f"Download di {branch}…")
        def worker():
            try:
                result = safe_extract_branch(branch)
                if result:
                    self.after(0, lambda: self.log_line(f"Versione scaricata in: {result}"))
                else:
                    self.after(0, lambda: self.log_line("Download annullato."))
            except Exception as error:
                self.report_error("Download non riuscito", str(error))
        threading.Thread(target=worker, daemon=True).start()

    def launch(self):
        branch = self.branch_var.get()
        if not branch:
            messagebox.showwarning("Nessun branch", "Seleziona un branch.")
            return
        version_dir = os.path.join(APP_ROOT, version_category(branch), safe_branch(branch))
        if not os.path.isdir(version_dir):
            if messagebox.askyesno("Versione non scaricata", "Scaricare questa versione adesso?"):
                self.download()
            return
        mode = CONFIG.get("start_mode", "file")
        if mode in ("file", "both"):
            main = find_main(version_dir, CONFIG.get("main_file", "index.html"))
            if main:
                os.startfile(main)
                self.log_line(f"Aperto: {main}")
            else:
                messagebox.showwarning("File non trovato", f"Non trovo {CONFIG.get('main_file')} in questa versione.")
        if mode in ("server", "both"):
            try:
                relative = CONFIG.get("server_directory", ".")
                working_dir = os.path.normpath(os.path.join(version_dir, relative))
                if not os.path.isdir(working_dir):
                    raise RuntimeError(f"Cartella server inesistente: {working_dir}")
                command = CONFIG.get("server_command", "").strip()
                if not command:
                    raise RuntimeError("Il comando del server è vuoto.")
                subprocess.Popen(command, cwd=working_dir, shell=True)
                url = CONFIG.get("server_url", "").strip()
                if url:
                    self.after(1200, lambda: webbrowser.open(url))
                self.log_line(f"Avviato comando server nella cartella: {working_dir}")
            except Exception as error:
                messagebox.showerror("Avvio server non riuscito", str(error))


if __name__ == "__main__":
    Assembler().mainloop()
