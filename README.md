# App Assembler Generator

Generatore Windows in Python con interfaccia grafica. Crea un assemblatore personalizzato per ogni repository GitHub pubblica.

## Requisiti

- Windows 10/11
- Python 3.10 o successivo, con Tkinter disponibile
- Connessione Internet per leggere e scaricare i branch GitHub

Non sono richieste librerie Python esterne nella versione 0.1.

## Avvio

1. Scarica questa repository con **Code → Download ZIP** ed estrai la cartella.
2. Fai doppio clic su `avvia_generatore.bat`.
3. Inserisci nome dell'app, URL GitHub e cartella di destinazione.
4. Scegli file principale e modalità di avvio.
5. Premi **Crea assemblatore**.
6. Apri `bot/avvia_assemblatore.bat` nella cartella appena creata.

## Cosa crea

- `bot/`: assemblatore, configurazione JSON e file BAT di avvio
- `versioni_0.x/`
- `versione_1.0/`
- `versioni_1.1_plus/`
- `versioni_altre/` per branch non numerici o versioni non riconosciute
- `backup/`: copie dei file testuali supportati, con suffisso `.txt`

Le versioni originali mantengono i nomi e le estensioni dei file. I file binari vengono scaricati normalmente, ma non inclusi nel backup testuale.

## Funzioni della versione 0.1

- Interfaccia grafica Tkinter
- Repository GitHub pubbliche
- Elenco dei primi 100 branch
- Download del branch selezionato
- Backup testuali
- Apertura del file principale, avvio server locale o entrambe le modalità

## Note

- In modalità **Entrambi**, l'assemblatore apre il file configurato e avvia anche il server. Se l'app richiede un server, scegli **Server locale** per evitare di aprire il file direttamente.
- Il comando del server viene eseguito nella cartella selezionata tramite configurazione. Esegui solo comandi che riconosci e di cui ti fidi.
- Le cartelle di versioni non riconosciute vengono salvate in `versioni_altre/`.
- Prima di sostituire una versione esistente, l'assemblatore chiede conferma e salva i file testuali esistenti nel backup.

## Roadmap

- 0.2: paginazione branch e migliore riconoscimento versioni
- 0.3: gestione server più chiara e selezione della cartella del progetto
- 0.4: controlli di integrità e riepilogo dei file scaricati
