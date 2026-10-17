import io
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import urllib.request
import webbrowser
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
APP_ROOT = HERE.parent
with (HERE / "config.json").open("r", encoding="utf-8") as stream:
    CONFIG = json.load(stream)

TEXT_EXTENSIONS = {
    ".html", ".htm", ".css", ".js", ".mjs", ".cjs", ".json", ".py", ".txt",
    ".md", ".xml", ".svg", ".yml", ".yaml", ".toml", ".ini", ".csv", ".ts",
    ".tsx", ".jsx", ".java", ".c", ".h", ".cpp", ".hpp", ".cs", ".php",
    ".rb", ".go", ".rs", ".sh", ".bat", ".ps1", ".sql"
}


def api_json(url):
    request = urllib.request.Request(url, headers={
        "User-Agent": "AppAssembler/0.2",
        "Accept": "application/vnd.github+json"
    })
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def get_branches():
    result = []
    page = 1
    while page <= 10:
        url = f"https://api.github.com/repos/{CONFIG['owner']}/{CONFIG['repository']}/branches?per_page=100&page={page}"
        batch = api_json(url)
        if not batch:
            break
        result.extend(item["name"] for item in batch)
        if len(batch) < 100:
            break
        page += 1
    return result


def safe_branch(branch):
    return re.sub(r"[^A-Za-z0-9._-]+", "_", branch).strip("._") or "branch"


def version_category(branch):
    match = re.fullmatch(r"v?(\d+)\.(\d+)(?:\.(\d+))?", branch.strip(), re.I)
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


def backup_files(branch, source_dir, label=""):
    if not CONFIG.get("backup_text_files_only", True):
        return
    backup_root = APP_ROOT / "backup" / safe_branch(branch)
    if label:
        backup_root = backup_root / label
    for path in source_dir.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in TEXT_EXTENSIONS:
            continue
        relative = path.relative_to(source_dir)
        destination = backup_root / (str(relative) + ".txt")
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)


def download_branch(branch):
    category = version_category(branch)
    target = APP_ROOT / category / safe_branch(branch)
    if target.exists():
        answer = input(f"La versione esiste già: {target}\nSostituirla? [s/N]: ").strip().lower()
        if answer not in {"s", "si", "sì", "y", "yes"}:
            print("Download annullato.")
            return None
        backup_files(branch, target, "precedente")
        shutil.rmtree(target)

    url = f"https://api.github.com/repos/{CONFIG['owner']}/{CONFIG['repository']}/zipball/{branch}"
    request = urllib.request.Request(url, headers={"User-Agent": "AppAssembler/0.2"})
    print(f"Download del branch {branch}…")
    with urllib.request.urlopen(request, timeout=90) as response:
        archive_data = response.read()

    target.mkdir(parents=True, exist_ok=True)
    try:
        with zipfile.ZipFile(io.BytesIO(archive_data)) as archive:
            members = archive.infolist()
            roots = {member.filename.split("/", 1)[0] for member in members if member.filename}
            if len(roots) != 1:
                raise RuntimeError("Struttura ZIP GitHub inattesa: radice non univoca.")
            prefix = next(iter(roots)) + "/"
            for member in members:
                name = member.filename
                if not name.startswith(prefix):
                    continue
                relative_text = name[len(prefix):]
                if not relative_text:
                    continue
                relative = Path(relative_text)
                if relative.is_absolute() or ".." in relative.parts:
                    raise RuntimeError(f"Percorso non sicuro nell'archivio: {relative_text}")
                destination = target / relative
                if member.is_dir():
                    destination.mkdir(parents=True, exist_ok=True)
                    continue
                destination.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(member) as source, destination.open("wb") as output:
                    shutil.copyfileobj(source, output)
    except Exception:
        if target.exists():
            shutil.rmtree(target, ignore_errors=True)
        raise
    backup_files(branch, target)
    print(f"Versione scaricata in: {target}")
    return target


def version_dirs():
    found = []
    for category in ("versioni_0.x", "versione_1.0", "versioni_1.1_plus", "versioni_altre"):
        folder = APP_ROOT / category
        if folder.is_dir():
            found.extend(path for path in folder.iterdir() if path.is_dir())
    return sorted(found, key=lambda path: (version_category(path.name), path.name.lower()))


def choose_version(require_downloaded=True):
    try:
        branches = get_branches()
    except Exception as error:
        print(f"Non riesco a leggere i branch GitHub: {error}")
        branches = []
    if branches:
        print("\nBranch disponibili su GitHub:")
        for i, branch in enumerate(branches, 1):
            local = APP_ROOT / version_category(branch) / safe_branch(branch)
            mark = " [scaricato]" if local.is_dir() else ""
            print(f"  {i}. {branch}{mark}")
        print("  0. Indietro")
        choice = input("Scegli il numero del branch: ").strip()
        if choice == "0" or not choice:
            return None
        try:
            branch = branches[int(choice) - 1]
        except (ValueError, IndexError):
            print("Scelta non valida.")
            return None
        local = APP_ROOT / version_category(branch) / safe_branch(branch)
        if require_downloaded and not local.is_dir():
            answer = input("Questa versione non è scaricata. Scaricarla ora? [S/n]: ").strip().lower()
            if answer not in {"n", "no"}:
                return download_branch(branch)
            return None
        return local if local.is_dir() else branch
    print("Elenco branch non disponibile; puoi scegliere una versione già scaricata.")
    dirs = version_dirs()
    for i, path in enumerate(dirs, 1):
        print(f"  {i}. {path.relative_to(APP_ROOT)}")
    if not dirs:
        print("Nessuna versione scaricata.")
        return None
    try:
        choice = int(input("Numero versione (0 per indietro): ").strip())
        return dirs[choice - 1] if 1 <= choice <= len(dirs) else None
    except (ValueError, IndexError):
        print("Scelta non valida.")
        return None


def find_main(directory):
    configured = CONFIG.get("main_file", "index.html")
    direct = directory / configured
    if direct.is_file():
        return direct
    wanted = Path(configured).name.lower()
    for path in directory.rglob("*"):
        if path.is_file() and path.name.lower() == wanted:
            return path
    return None


def launch_version():
    selected = choose_version(require_downloaded=True)
    if selected is None:
        return
    if isinstance(selected, str):
        selected = download_branch(selected)
        if selected is None:
            return
    mode = CONFIG.get("start_mode", "file")
    if mode in ("file", "both"):
        main = find_main(selected)
        if main:
            try:
                os.startfile(str(main))
                print(f"Aperto: {main}")
            except OSError as error:
                print(f"Impossibile aprire il file: {error}")
        else:
            print(f"File principale non trovato: {CONFIG.get('main_file', 'index.html')}")
    if mode in ("server", "both"):
        relative = Path(CONFIG.get("server_directory", "."))
        if relative.is_absolute() or ".." in relative.parts:
            print("Cartella server non sicura nella configurazione.")
            return
        working = (selected / relative).resolve()
        if not working.is_dir() or selected.resolve() not in (working, *working.parents):
            print("Cartella server non valida.")
            return
        command = CONFIG.get("server_command", "").strip()
        if not command:
            print("Il comando server non è configurato.")
            return
        try:
            args = shlex.split(command, posix=(os.name != "nt"))
            subprocess.Popen(args, cwd=str(working))
            url = CONFIG.get("server_url", "").strip()
            if url:
                webbrowser.open(url)
            print(f"Server avviato nella cartella {working}")
        except Exception as error:
            print(f"Avvio server non riuscito: {error}")


def resolve_path(raw):
    candidate = Path(raw).expanduser()
    if not candidate.is_absolute():
        candidate = APP_ROOT / candidate
    return candidate.resolve()


def file_manager():
    features = set(CONFIG.get("file_manager_features", []))
    custom = CONFIG.get("custom_commands", [])
    while True:
        print("\n=== GESTIONE FILE ===")
        print(f"Radice app: {APP_ROOT}")
        actions = []
        menu = {
            "list": ("Elencare file e cartelle", list_files),
            "search": ("Cercare file per nome", search_files),
            "open": ("Aprire file/cartelle", open_path),
            "copy": ("Copiare file/cartelle", copy_path),
            "rename": ("Rinominare file/cartelle", rename_path),
            "delete": ("Eliminare file/cartelle", delete_path),
            "create": ("Creare cartelle", create_folder),
            "backup": ("Backup e ripristino", backup_menu),
            "versions": ("Confrontare versioni", compare_versions),
            "logs": ("Cronologia operazioni", show_logs),
        }
        for key, (label, function) in menu.items():
            if key in features:
                actions.append((label, function))
        for item in custom:
            actions.append((f"Comando personalizzato: {item['name']} - {item['description']}", lambda item=item: run_custom(item)))
        for i, (label, _) in enumerate(actions, 1):
            print(f"  {i}. {label}")
        print("  0. Indietro")
        try:
            choice = int(input("Selezione: ").strip())
        except ValueError:
            print("Inserisci un numero.")
            continue
        if choice == 0:
            return
        if 1 <= choice <= len(actions):
            try:
                actions[choice - 1][1]()
            except Exception as error:
                print(f"Operazione non riuscita: {error}")
            pause()
        else:
            print("Scelta non valida.")


def pause():
    input("\nPremi Invio per continuare…")


def log_operation(text):
    log_file = APP_ROOT / "backup" / "cronologia.txt"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with log_file.open("a", encoding="utf-8") as stream:
        stream.write(text + "\n")


def list_files():
    raw = input("Percorso da elencare (Invio = radice app): ").strip() or "."
    path = resolve_path(raw)
    if not path.is_dir():
        print("La cartella non esiste.")
        return
    for item in sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
        print(("[DIR] " if item.is_dir() else "[FILE] ") + item.name)


def search_files():
    query = input("Nome o parte del nome da cercare: ").strip().lower()
    if not query:
        print("Ricerca vuota.")
        return
    start = resolve_path(input("Cartella iniziale (Invio = radice app): ").strip() or ".")
    if not start.is_dir():
        print("La cartella non esiste.")
        return
    count = 0
    for path in start.rglob("*"):
        if query in path.name.lower():
            print(path)
            count += 1
    print(f"Risultati: {count}")


def open_path():
    path = resolve_path(input("Percorso da aprire: ").strip())
    if not path.exists():
        print("Percorso non trovato.")
        return
    if os.name == "nt":
        os.startfile(str(path))
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])
    log_operation(f"APERTO {path}")


def copy_path():
    source = resolve_path(input("Percorso sorgente: ").strip())
    destination = resolve_path(input("Percorso destinazione: ").strip())
    if not source.exists():
        print("Sorgente non trovata.")
        return
    if destination.exists():
        print("Destinazione già esistente: non sovrascrivo.")
        return
    if source.is_dir():
        shutil.copytree(source, destination)
    else:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    log_operation(f"COPIATO {source} -> {destination}")
    print("Copia completata.")


def rename_path():
    source = resolve_path(input("Percorso attuale: ").strip())
    if not source.exists():
        print("Percorso non trovato.")
        return
    new_name = input("Nuovo nome (solo nome, non percorso): ").strip()
    if not new_name or Path(new_name).name != new_name or new_name in {".", ".."}:
        print("Nome non valido.")
        return
    destination = source.with_name(new_name)
    if destination.exists():
        print("Esiste già un file o una cartella con quel nome.")
        return
    source.rename(destination)
    log_operation(f"RINOMINATO {source} -> {destination}")
    print("Rinominato.")


def delete_path():
    target = resolve_path(input("Percorso da eliminare: ").strip())
    if not target.exists():
        print("Percorso non trovato.")
        return
    if target.resolve() == APP_ROOT.resolve() or target.resolve() == Path.home().resolve() or target == Path(target.anchor):
        print("Percorso protetto: non può essere eliminato.")
        return
    print(f"ATTENZIONE: verrà eliminato definitivamente: {target}")
    if input("Scrivi ELIMINA per confermare: ").strip() != "ELIMINA":
        print("Annullato.")
        return
    if target.is_dir():
        shutil.rmtree(target)
    else:
        target.unlink()
    log_operation(f"ELIMINATO {target}")
    print("Eliminato.")


def create_folder():
    target = resolve_path(input("Percorso della nuova cartella: ").strip())
    target.mkdir(parents=True, exist_ok=False)
    log_operation(f"CREATA CARTELLA {target}")
    print(f"Creata: {target}")


def backup_menu():
    print("  1. Copia di sicurezza di un file/cartella")
    print("  2. Ripristina da un file di backup")
    choice = input("Selezione: ").strip()
    source = resolve_path(input("Percorso sorgente/backup: ").strip())
    if not source.exists():
        print("Percorso non trovato.")
        return
    if choice == "1":
        destination = APP_ROOT / "backup" / "manuali" / (source.name + ".backup")
        destination.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            if destination.exists():
                print("Il backup esiste già.")
                return
            shutil.copytree(source, destination)
        else:
            shutil.copy2(source, destination)
        print(f"Backup creato: {destination}")
    elif choice == "2":
        destination = resolve_path(input("Percorso destinazione ripristino: ").strip())
        if destination.exists():
            print("Destinazione già esistente; non sovrascrivo.")
            return
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        print(f"Ripristinato in: {destination}")
    else:
        print("Scelta non valida.")


def compare_versions():
    dirs = version_dirs()
    if not dirs:
        print("Nessuna versione scaricata.")
        return
    for path in dirs:
        count = sum(1 for item in path.rglob("*") if item.is_file())
        print(f"{path.relative_to(APP_ROOT)}: {count} file")


def show_logs():
    path = APP_ROOT / "backup" / "cronologia.txt"
    if not path.is_file():
        print("Nessuna operazione registrata.")
        return
    print(path.read_text(encoding="utf-8"))


def run_custom(item):
    print(f"{item['name']}: {item['description']}")
    print(f"Comando configurato: {item['command']}")
    if input("Eseguire questo comando? [s/N]: ").strip().lower() not in {"s", "si", "sì", "y", "yes"}:
        print("Annullato.")
        return
    # Comando configurato dall'utente; esecuzione esplicita dopo conferma.
    subprocess.run(item["command"], cwd=str(APP_ROOT), shell=True, check=False)
    log_operation(f"COMANDO PERSONALIZZATO {item['name']}")


def main():
    while True:
        print(f"\n=== {CONFIG['app_name']} · ASSEMBLATORE ===")
        print(f"Repository: {CONFIG['repository_url']}")
        print("  1. Scarica una versione da GitHub")
        print("  2. Avvia una versione")
        print("  3. Elenca versioni scaricate")
        if CONFIG.get("enable_file_manager", False):
            print("  4. Gestione file")
        print("  0. Esci")
        choice = input("Selezione: ").strip()
        if choice == "0":
            return
        if choice == "1":
            selected = choose_version(require_downloaded=False)
            if isinstance(selected, str):
                try:
                    download_branch(selected)
                except Exception as error:
                    print(f"Download non riuscito: {error}")
            elif selected is not None:
                print(f"Versione locale: {selected}")
            pause()
        elif choice == "2":
            launch_version()
            pause()
        elif choice == "3":
            dirs = version_dirs()
            if not dirs:
                print("Nessuna versione scaricata.")
            else:
                for path in dirs:
                    print(path.relative_to(APP_ROOT))
            pause()
        elif choice == "4" and CONFIG.get("enable_file_manager", False):
            file_manager()
        else:
            print("Scelta non valida.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nChiusura.")
