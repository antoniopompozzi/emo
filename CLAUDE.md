# EMO — memoria di progetto per Claude Code

Questo file va letto a inizio di ogni sessione. Serve a garantire continuità
senza dipendere dalla lunghezza della chat: resta piccolo e stabile nel
tempo (a differenza di una conversazione, che cresce ogni giorno con un
nuovo run automatico). Se una sessione si satura, aprine una nuova: questo
file la rimette subito al corrente, senza bisogno di ricostruire il
contesto a mano.

## Cos'è EMO

Una tavolozza quotidiana di pixel duotono (nero + un colore legato
all'emozione dominante) generata leggendo le principali notizie
internazionali del giorno. Nessun repertorio fisso di soggetti: EMO può
raffigurare letteralmente qualsiasi cosa. L'unico elemento sempre fisso è
la trasformazione finale in griglia di pixel a bordi netti.

**Principio metodologico centrale (non toccare senza discuterne prima):**
qui l'autore non controlla il *contenuto* dell'artefatto (libero, deciso
da Claude Haiku) ma solo la *regola/il comportamento* che lo genera
(pipeline fissa, post-produzione deterministica, palette emozione–colore
fissa, fallback deterministico). Ogni modifica proposta va valutata
chiedendosi se sposta un pezzo di libertà creativa verso la regola fissa,
o viceversa — è la distinzione più importante del progetto.

## Architettura

Un passaggio di raccolta dati alimenta i tre passaggi veri e propri del
progetto — due affidati all'IA, uno deterministico:

0. `pipeline/news.py` — input, non uno dei tre passaggi: legge le notizie
   (BBC World News RSS, Google News come fallback).
1. `pipeline/concept.py` **[IA]** — un'unica chiamata a Claude Haiku
   restituisce in JSON `concept` (prompt per l'immagine), `explanation`
   (testo pubblico) ed `emotion` (una parola fissa dalla palette, vedi
   sotto). La classificazione dell'emozione NON è un passaggio separato:
   è un campo dentro la stessa risposta JSON.
2. `pipeline/image_provider.py` **[IA]** — invia `concept` a OpenAI
   gpt-image-1.5 (1024x1024, qualità medium). L'immagine sorgente è
   quadrata fin dal primissimo commit del repo (già ai tempi di
   Pollinations, il provider precedente) — non è mai esistito un formato
   panoramico.
3. `pipeline/postprocess.py` **[deterministico]** — trasformazione fissa
   (Pillow/numpy): scala di grigi, downsampling a griglia fitta
   (box filter), quantizzazione dei livelli di grigio, duotono nero +
   colore dell'emozione, bordi netti (nearest-neighbour, nessun
   antialiasing).

A valle, non tra i tre passaggi: `pipeline/archive.py` scrive tutto su
`archive/<data>/` (vedi elenco file sotto), `website/build_site.py` genera
il sito statico da lì.

## Palette emozione → colore (`pipeline/emotions.py`)

Sei delle sei emozioni base di Ekman (non la "contempt" a volte aggiunta
come settima), più una categoria pratica "neutral" per quando nessuna
emozione domina o per i fallback:

| Emozione | Colore |
|---|---|
| anger | #c0392b |
| sadness | #2e5c9a |
| fear | #5b2c6f |
| joy | #d4a017 |
| surprise | #1a9e8f |
| disgust | #556b2f |
| neutral (default) | #555555 |

## Fallback: due flag indipendenti in ogni `metadata.json`

Ciascuno dei due ha due possibili cause, che portano allo stesso risultato
(vedi `pipeline/main.py`, non solo `concept.py`/`image_provider.py`):
manca del tutto la variabile d'ambiente della chiave, oppure la chiave
c'è ma la chiamata fallisce (o restituisce JSON non valido) dopo tutti i
retry.

- `concept_used_fallback: true` — niente `ANTHROPIC_API_KEY`, o chiamata a
  Claude Haiku fallita. Concept ed explanation diventano un testo fisso
  onesto ("Today EMO could not read the news..."), ed **emotion viene
  forzata a "neutral" → grigio #555555** (`FALLBACK_CONCEPT` in
  `concept.py` include esplicitamente `"emotion": DEFAULT_EMOTION`).
- `image_used_fallback: true` — niente `OPENAI_API_KEY`, o chiamata a
  OpenAI fallita. L'emozione/colore reali restano quelli classificati
  (il concept step è comunque riuscito); solo l'immagine sorgente diventa
  un placeholder locale deterministico (seed = hash del testo del
  concept).

Entrambi i flag vengono dichiarati onestamente nel modale "why this
image?" di quel giorno (`_hero.html`) — non vanno mai nascosti lì.
`website/build_site.py` esclude però i giorni con uno dei due flag a
`true` (funzione `is_fallback_day`) dalla lista `gallery_days` passata al
template `archive.html`, quindi non compaiono come miniatura nella
griglia della pagina archivio. È un filtro solo sulla griglia: la lista
`days` non filtrata continua a essere usata per generare normalmente la
pagina singola `days/<data>/` di quel giorno (che resta raggiungibile e
mostra comunque la nota di fallback in `_hero.html`), per l'homepage se
quel giorno fosse il più recente, e per `sitemap.xml`/`robots.txt`.

## Dominio, SEO e condivisione

- Il sito vive su **emopixels.xyz** (dominio custom collegato dalle
  impostazioni del repository su GitHub, non da un file `CNAME` nel
  codice). `config.yaml` → `site.base_url` deve restare allineato a
  questo dominio: è la base per tutti gli URL assoluti (Open Graph,
  `robots.txt`, `sitemap.xml`). Il vecchio URL
  `antoniopompozzi.github.io/emo/` reindirizza automaticamente al nuovo
  dominio (comportamento di GitHub Pages, non qualcosa che il codice deve
  gestire).
- `website/build_site.py` genera anche `robots.txt` e `sitemap.xml` ad
  ogni build. La pagina dell'ultimo giorno (`days/<ultima-data>/`) e la
  homepage renderizzano contenuto identico byte per byte (stesso
  `_hero.html`, vedi sotto): per questo `days/<ultima-data>/` dichiara
  `rel="canonical"` verso la homepage invece che verso se stessa, ed è
  volutamente esclusa da `sitemap.xml` — non è un bug, è la scelta che
  evita di segnalare ai motori di ricerca due URL con contenuto duplicato.
- `pipeline/share_card.py` genera due varianti, entrambe a partire da
  `final_image` e condividendo la stessa logica di badge
  (`_badge_layout`, `_draw_pixel_badge`, `_draw_date_and_emotion_badges`
  — se si cambia una proporzione, va cambiata lì una volta sola):
  - `render_share_card()` — quadrata (`share_card.size` in
    `config.yaml`, default 1080), badge sovrapposti all'immagine. Usata
    dal sito: bottone SHARE, download, `og:image`/`twitter:image`.
  - `render_instagram_card()` — fissa 1080x1350 (4:5, formato feed
    Instagram), badge nei margini bianchi sopra/sotto invece che
    sovrapposti. **Non è integrata nel sito né negli Open Graph tag**:
    resta solo in `archive/<data>/instagram_card.png` per uso
    manuale/futuro. Non è codice morto, non rimuoverla in un audit di
    pulizia.
  - Il font Press Start 2P è vendorizzato in
    `website/static/fonts/PressStart2P-Regular.ttf` (licenza OFL) perché
    Pillow non può leggere il foglio di stile di Google Fonts che usa il
    browser.
- `og:title`/`og:description`/una `<meta name="description">` fissa
  compaiono su ogni pagina, anche i giorni archiviati prima
  dell'esistenza di `share_card.png`; `og:image`/`twitter:image` compaiono
  solo quando quel giorno ha davvero una `share_card.png`.
- Il bottone SHARE (in basso a sinistra, speculare a WHY THIS
  IMAGE?/ARCHIVE) apre **sempre e solo** un modale personalizzato
  (anteprima, download, copia link) — vedi "Cronologia" sotto per il
  perché non usa la Web Share API nativa del browser.

## Automazione (`.github/workflows/daily.yml`)

- Cron `"7 6 * * *"` (06:07 UTC, non 06:00) — offset deliberato per
  evitare i ritardi che GitHub Actions accumula sui minuti tondi a inizio
  ora. Non "correggerlo" tornando a 0.
- Tre modi in cui il workflow parte: schedule (sopra), `workflow_dispatch`
  manuale (anche su un branch di feature, utile per testare una vera
  chiamata OpenAI prima di mergiare), push su `main` (ignorando i push che
  toccano solo `archive/`, cioè i suoi stessi commit automatici).
- **Solo schedule e dispatch rigenerano un nuovo giorno** (eseguono
  `pipeline.main`, quindi consumano credito Anthropic/OpenAI). Un push su
  main (es. merge di un fix a `style.css` o `build_site.py`) salta quello
  step: ricostruisce e ripubblica il sito da quello che è già in
  `archive/`, senza rigenerare nulla. Per questo un fix di stile/HTML va
  online subito dopo il merge, senza aspettare la run delle 06:07 e senza
  costare nulla in più.
- Il deploy vero e proprio (pubblicazione su GitHub Pages) gira solo se
  `github.ref == 'refs/heads/main'` — guardia già in vigore, non toccarla:
  un dispatch manuale su un branch di feature esegue la pipeline e
  committa il risultato su quel branch, ma non pubblica.

### Trigger esterno (Cloudflare Worker) e idempotenza

Lo `schedule:` nativo di GitHub Actions si è dimostrato inaffidabile
(il 27/08/2026 non è scattato all'orario previsto — mancato trigger
dello scheduler GitHub, non un fallimento della pipeline). Da allora un
**Cloudflare Worker** (`infra/cloudflare-worker/trigger-daily-emo.js`,
vedi il README nella stessa cartella per dove incollarlo e come
configurarlo) affianca un secondo trigger indipendente: un proprio Cron
Trigger a `3 6 * * *` (06:03 UTC) chiama l'endpoint `workflow_dispatch`
dell'API GitHub sullo stesso `daily.yml`. Lo `schedule:` delle 06:07
resta al suo posto come rete di sicurezza residua — non va rimosso.

Con due trigger indipendenti sullo stesso workflow nello stesso giorno,
`pipeline.main.run()` è **idempotente rispetto alla data odierna
(UTC)**: prima di chiamare Claude o gpt-image-1.5, controlla se
`archive/<data-di-oggi>/metadata.json` esiste già; se sì, stampa
`"Archivio già presente per {data}, salto la generazione."` e ritorna
subito senza toccare l'archivio esistente, lasciando che gli step
successivi del workflow (build/deploy del sito) procedano comunque a
ricostruire da quanto già presente. Questa è una protezione
**complementare**, non sostitutiva, al guard `if:
github.event_name != 'push'` già presente sugli step "Run daily
pipeline"/"Commit new archive entry": quel guard copre i push di
codice, questa copre due trigger che generano per lo stesso giorno.
Non rimuovere né l'uno né l'altro pensando che si siano resi ridondanti
a vicenda.

Il token `GITHUB_PAT` che il Worker usa per autenticarsi vive solo come
variabile d'ambiente **Encrypt** nel dashboard Cloudflare del Worker,
mai in questo repository.

## File per giorno in `archive/<data>/` (oltre a `metadata.json`)

- `final.png` — l'immagine pubblicata.
- `source.png` — l'immagine grezza prima della pixelazione.
- `share_card.png` — usata dal sito (bottone SHARE, `og:image`).
- `instagram_card.png` — 1080x1350 (4:5), badge nei margini invece che
  sovrapposti; **non usata dal sito**, tenuta per uso manuale/futuro. Non
  è codice morto: non rimuoverla in un audit di pulizia.
- `grid_values.json` — griglia di luminosità quantizzata + emozione/colore,
  traccia grezza per la tesi, non letta dal sito pubblicato.
- `exchange_log.json` — log completo di richieste/risposte a Claude e a
  OpenAI per quel giorno; utile per diagnosticare una run fallita senza
  dover ricostruire cosa è successo da altrove.

I giorni archiviati prima dell'esistenza di una feature (es. `share_card.png`,
`instagram_card.png`, il campo `emotion` in `metadata.json`) possono non
avere quel file/campo: tutto il codice a valle (build del sito, generatori
di card) deve degradare con grazia, non assumere che sia sempre presente.

## Cronologia architetturale essenziale (per non riproporre idee già scartate)

- Il rendering del duotono lato browser su `<canvas>` (disegnato a partire
  da `grid_values.json`, per adattare la dimensione delle celle a
  qualunque schermo) è stato provato e poi abbandonato: l'immagine
  risultava poco leggibile. Architettura attuale: `final.png` generato e
  mostrato lato server, scalato e centrato, mai ritagliato —
  `grid_values.json` continua a essere scritto ogni giorno ma solo come
  traccia grezza per la tesi, non è più letto da alcun codice del sito
  pubblicato.
- L'effetto "pulsanti magnetici" (il bottone si spostava leggermente
  verso il cursore al passaggio del mouse, con una `transition: transform
  ease-out` vera e propria) è stato aggiunto e poi rimosso su richiesta
  esplicita dell'autore ("non mi piace più") — non ha violato nessuna
  regola di design preesistente, è stata una scelta estetica a posteriori.
  Non reintrodurlo senza che l'autore lo richieda esplicitamente. (Non
  esiste una regola generale "mai transizioni morbide": i pulsanti
  cambiano colore all'hover/focus istantaneamente semplicemente perché
  nessuna `transition` è dichiarata in CSS, non per un vincolo di design
  dichiarato.)
- Il bottone SHARE inizialmente provava prima la Web Share API nativa del
  browser (`navigator.share`/`canShare`, con file allegato), con il
  modale personalizzato come ripiego. Rimossa del tutto (non disattivata)
  su richiesta esplicita: il picker di sistema si comportava in modo
  incoerente tra browser (lista di app irrilevanti su Windows/Edge,
  comportamento cambiato nel tempo su Firefox). Ora il click su SHARE
  apre sempre e solo lo stesso modale personalizzato, identico su ogni
  dispositivo. Non reintrodurre `navigator.share`/`canShare` senza
  richiesta esplicita.
- Il cron è stato spostato da `"0 6 * * *"` a `"7 6 * * *"` (vedi
  "Automazione" sopra) per lo stesso motivo di sempre: non toccarlo di
  nuovo senza motivo.

## Cose da NON toccare senza conferma esplicita

- L'estetica pixel-art già validata (griglia, font Press Start 2P, alto
  contrasto bianco/nero/colore emozione).
- I file d'archivio non usati dal sito pubblicato (`grid_values.json`,
  `source.png`, `instagram_card.png`) — vedi "File per giorno" sopra: sono
  materiale grezzo/futuro tenuto di proposito, non codice morto.
- La Web Share API nativa (`navigator.share`/`canShare`) — rimossa
  deliberatamente dal bottone SHARE, vedi "Cronologia" sopra.
- Il guard `github.ref == 'refs/heads/main'` sul job `deploy` in
  `daily.yml` — è l'unica cosa che impedisce a un dispatch manuale su un
  branch di feature di pubblicare per sbaglio.
- Il controllo di idempotenza in `pipeline/main.py` (skip se
  `archive/<data>/metadata.json` esiste già) e il guard `if:
  github.event_name != 'push'` in `daily.yml` — sono due protezioni
  complementari per due problemi diversi (trigger duplicati nello stesso
  giorno vs. push di codice), non rimuoverne una pensando che l'altra
  basti.

## Protocollo di sicurezza (sempre)

- Tag di ripristino su GitHub prima di ogni intervento (`prima-di-<nome>`).
- Branch dedicato (`feature/<nome>`), mai commit diretti su `main`.
- Un commit per task, non commit unici enormi.
- Verifica che `pytest` passi dopo ogni modifica.
- Verifica visiva (idealmente Playwright sul sito live, non solo
  localhost) prima di dichiarare un task concluso.
- Nessun merge/deploy su `main` senza conferma esplicita dell'autore.
- Qualunque task che cambia un comportamento già documentato in questo
  file deve aggiornare CLAUDE.md nello stesso branch, in un commit
  separato, prima di fermarsi per la conferma di merge — non lasciarlo
  disallineato per una sessione futura.

## Segreti

`ANTHROPIC_API_KEY` e `OPENAI_API_KEY` sono secret di GitHub Actions sul
repository, mai nel codice. Il credito Anthropic si ricarica su
console.anthropic.com.

`GITHUB_PAT` (usato dal Cloudflare Worker per innescare `workflow_dispatch`,
vedi "Automazione" sopra) è una variabile Encrypt nel dashboard Cloudflare
del Worker, non un secret di questo repository — non va mai gestito da
Claude Code in questa sessione né in nessun'altra.
