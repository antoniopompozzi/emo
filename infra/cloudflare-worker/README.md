# Trigger esterno EMO — Cloudflare Worker

## Perché esiste

Lo schedule: nativo di GitHub Actions (`.github/workflows/daily.yml`,
cron `"7 6 * * *"`) si è dimostrato inaffidabile: il 27/08/2026 non è
scattato all'orario previsto (mancato trigger dello scheduler GitHub,
non un fallimento della pipeline). Questo Worker affianca un secondo
trigger, indipendente dallo scheduler di GitHub, che chiama l'endpoint
`workflow_dispatch` dell'API GitHub sullo stesso workflow. Lo
`schedule:` nativo resta al suo posto come rete di sicurezza residua,
non viene rimosso.

Con due trigger sullo stesso workflow nello stesso giorno, `pipeline/main.py`
è stato reso idempotente rispetto alla data odierna (vedi CLAUDE.md e
il commit corrispondente): se una delle due run arriva quando
l'archivio del giorno esiste già, salta la generazione invece di
rigenerare l'immagine da zero.

## Cosa fa `trigger-daily-emo.js`

Un Worker Cloudflare con un proprio Cron Trigger che, quando scatta,
invia una richiesta `POST` autenticata a
`https://api.github.com/repos/antoniopompozzi/emo/actions/workflows/daily.yml/dispatches`
con `{ "ref": "main" }`, esattamente come premere manualmente "Run
workflow" su GitHub Actions. Non contiene altra logica: nessun accesso
a dati EMO, nessuna dipendenza da questo repository a runtime.

Non viene eseguito da GitHub Actions — è uno script a sé che gira
sull'infrastruttura Cloudflare, indipendente da questo repo dopo essere
stato incollato nel dashboard.

## Dove va incollato

1. Dashboard Cloudflare → **Workers & Pages** → **Create** → **Create
   Worker**.
2. Dai al Worker un nome (es. `emo-daily-trigger`).
3. Apri l'editor del Worker e sostituisci il contenuto di default con
   tutto il contenuto di [`trigger-daily-emo.js`](./trigger-daily-emo.js).
4. **Deploy**.

## Variabile d'ambiente attesa

| Nome | Tipo | Valore |
|---|---|---|
| `GITHUB_PAT` | **Encrypt** (secret) | Personal Access Token GitHub con permesso `actions: write` sul repository `antoniopompozzi/emo` (un token fine-grained scoped al solo repo è sufficiente; non serve altro scope) |

Impostala da: Worker → **Settings** → **Variables and Secrets** →
**Add** → nome `GITHUB_PAT`, valore il token, tipo **Encrypt**. Il
Worker la legge come `env.GITHUB_PAT`; non va mai scritta nel codice
dello script né committata in questo repository.

## Cron consigliato

```
3 6 * * *
```

06:03 UTC — tre minuti prima del fallback nativo delle 06:07 UTC
(`schedule:` in `daily.yml`). Se il Worker ha già fatto il suo lavoro,
la run delle 06:07 trova l'archivio del giorno già scritto e
l'idempotenza di `pipeline/main.py` la fa uscire subito senza
rigenerare nulla; se invece il Worker fallisce o non scatta, la run
delle 06:07 procede normalmente come unica generazione del giorno.

Si imposta da: Worker → **Settings** → **Trigger Events** → **Cron
Trigger** → **Add Cron Trigger**.

## Verifica dopo il deploy

Il modo più sicuro per verificare che il Worker chiami davvero
l'endpoint giusto è lanciarlo manualmente da Cloudflare (pulsante "Run"
sul trigger, o `wrangler dev` in locale con un `GITHUB_PAT` di prova) e
controllare in GitHub → Actions → daily.yml che compaia una nuova run
con evento `workflow_dispatch`. Nessuna di queste verifiche va fatta da
questa sessione: qui il Worker resta solo un file di testo pronto per
essere copiato a mano.
