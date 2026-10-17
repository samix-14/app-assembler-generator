# App Assembler Generator

Generatore Python con interfaccia grafica Tkinter che crea assemblatori personalizzati da terminale per repository GitHub pubbliche.

## Requisiti

- Windows 10/11 consigliato.
- Python 3.10 o successivo, con Tkinter.
- Connessione Internet per consultare e scaricare i branch GitHub.
- Nessuna libreria Python esterna richiesta.

## Avvio

1. Apri la repository e scegli **Code → Download ZIP**.
2. Estrai l'archivio.
3. Avvia `avvia_generatore.bat`.
4. Compila le tre sezioni della finestra: app/repository, avvio, gestione file.
5. Premi **Crea assemblatore**.
6. Nella cartella creata, avvia `bot/avvia_assemblatore.bat`.

## Il generatore crea

- `bot/assembler.py`: bot da terminale, non un'altra GUI.
- `bot/config.json`: configurazione per repository, avvio e funzioni scelte.
- `bot/avvia_assemblatore.bat`: avvio su Windows.
- `versioni_0.x/`, `versione_1.0/`, `versioni_1.1_plus/`, `versioni_altre/`.
- `backup/`: copie testuali con estensione aggiuntiva `.txt`.

I file originali conservano nome ed estensione. I backup vengono creati soltanto per le estensioni testuali supportate. Il programma chiede conferma prima di sostituire una versione già scaricata.

## Funzioni configurabili

Il bot può includere un menu di gestione file con le sole funzioni selezionate nel generatore: elenco, ricerca, apertura, copia, rinomina, eliminazione con conferma, creazione cartelle, backup/ripristino, riepilogo delle versioni e cronologia. Può inoltre mostrare comandi personalizzati inseriti nel formato:

`nome | descrizione | comando`

I comandi personalizzati eseguono un comando di sistema e richiedono una conferma esplicita. Inserisci solo comandi che capisci e di cui ti fidi.

## Versioni GitHub

Il bot consulta i branch della repository e li scarica come ZIP. I branch numerici vengono raggruppati nelle cartelle previste; gli altri vanno in `versioni_altre/`. Il bot gestisce fino a 1000 branch tramite paginazione dell'API pubblica, nei limiti imposti da GitHub.

## Avvio dell'app

- **Apri file**: apre il file principale con il programma predefinito di Windows.
- **Server locale**: avvia il comando configurato nella cartella relativa scelta e apre l'URL.
- **Entrambi**: esegue entrambe le azioni.

Usa soltanto repository e comandi affidabili. I programmi scaricati possono contenere codice eseguibile: il bot non li verifica come sicuri.

## Nota sullo stato

Il codice viene pubblicato su GitHub, ma deve ancora essere provato sul computer Windows di chi lo utilizza. Se qualcosa non funziona, conserva il messaggio d'errore completo per correggerlo in modo riproducibile.
