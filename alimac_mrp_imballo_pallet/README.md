# Alimac – Imballo pallet da produzione

| | |
|---|---|
| Modulo | `alimac_mrp_imballo_pallet` |
| Versione | 19.0.1.3.0 (Odoo 19) |
| Dipendenze | `mrp`, `sale_stock` |
| Autore | Progresso Srl |

## Indice

1. [A cosa serve](#1-a-cosa-serve)
2. [Flusso](#2-flusso)
3. [Chi fa cosa: modulo, wizard, configurazione manuale](#3-chi-fa-cosa-modulo-wizard-configurazione-manuale)
4. [Configurazione, passo per passo](#4-configurazione-passo-per-passo)
5. [Utilizzo](#5-utilizzo)
6. [Comportamento nei vari casi](#6-comportamento-nei-vari-casi)
7. [Cosa dipende da un nome](#7-cosa-dipende-da-un-nome)
8. [Migrazione dalle personalizzazioni Studio](#8-migrazione-dalle-personalizzazioni-studio)
9. [Limiti noti](#9-limiti-noti)
10. [Note tecniche](#10-note-tecniche)
11. [Test](#11-test)

---

## 1. A cosa serve

Alimac produce sempre in **sacchi** (o big bag). I pallet si fanno dopo, a produzione chiusa, e spesso la macchina fa qualche sacco in più dell'ordine.

Il modulo:

- **Pulsante Imballa** sull'ordine di produzione completato: divide i sacchi in colli secondo la confezione ordinata, crea i colli con la tipologia collo, scarica i materiali di imballo (pedana, film…) e convalida il trasferimento di imballo. I sacchi in più restano nell'ubicazione sacchi.
- **Convalida automatica**: flag sul tipo operazione che chiude da solo i trasferimenti intermedi (es. *Prelievo confezionato*), così all'utente resta solo la consegna.
- **Imballaggio sull'MO**: l'MO mostra cosa è stato ordinato (es. *2 Pallet 1500kg - 20kg x 75*) e avvisa se il formato ordinato non corrisponde all'unità di produzione.
- **Giacenze leggibili**: colonne *N* (quantità nell'unità di conteggio dell'ubicazione, es. numero di sacchi), *Tipologia collo* e *N colli*.
- **Wizard Configura formato confezionato**: crea in un colpo ubicazione, tipo operazione e rotta di un formato.
- **All'installazione**: ubicazione virtuale *Consumo Imballi* e migrazione delle personalizzazioni Studio esistenti.

Nessun imballaggio è scritto nel codice: sacchi per collo, tipologie collo e materiali vengono tutti dalla configurazione (sezione 4).

## 2. Flusso

**Rotta pallet** (es. *Vendita confezionato Pallet 1500kg - 20kg x 75*), dall'ordine alla consegna:

| # | Passo | Da → A | Tipo operazione | Chi lo chiude |
|---|---|---|---|---|
| 1 | Produzione sacchi | `WH/Giacenza` → `WH/Confezionato/Sacco20kg` | Produzione - Sacco 20kg | Operatore (chiude l'MO) |
| 2 | Imballo | `Sacco20kg` → `Pallet 1500kg - 20kg x 75` | Imballo Pallet… | Pulsante **Imballa** |
| 3 | Prelievo | `Pallet…` → `WH/Confezionato` | Prelievo confezionato | **Convalida automatica** |
| 4 | Consegna | `WH/Confezionato` → Clienti | Ordini di consegna | Utente |

**Rotta sacchi o big bag** (es. *Vendita confezionato Sacco 25kg*): come sopra senza il passo 2. La produzione va in `Sacco25kg`, il prelievo si chiude da solo e resta la consegna.

Esempio: ordine di 2 pallet da 75 sacchi, la macchina ne fa 160.

1. L'MO chiede 150 Sacco 20kg; si chiude dichiarando 160.
2. **Imballa**: 2 colli da 75 sacchi in `Pallet…`, scarico di 2 pedane e 2 dosi di film.
3. Il prelievo si convalida da solo e porta i 2 colli in `WH/Confezionato`.
4. La consegna è pronta con i 2 colli.
5. 10 sacchi restano in `Sacco20kg`, disponibili per il prossimo ordine.

## 3. Chi fa cosa: modulo, wizard, configurazione manuale

| Elemento | Chi lo crea | Dove |
|---|---|---|
| Unità sacchi, big bag, pallet (con tipologia collo) | **A mano** | Prodotto / Unità di misura (4.1) |
| Tipologie collo | **A mano** | Inventario → Configurazione → Tipologie collo (4.1) |
| Prodotti di imballo (pedana, film…) | **A mano** | Prodotti (4.1) |
| Materiali per tipologia collo | **A mano** | Tipologia collo → scheda *Materiali di imballo* (4.1) |
| Ubicazione `WH/Confezionato` | **A mano** (una volta) | Ubicazioni (4.2) |
| Tipo operazione *Prelievo confezionato* | **A mano** (una volta) | Tipi di operazione (4.2) |
| Ubicazione virtuale *Consumo Imballi* | Modulo, all'installazione | — |
| Ubicazione di ogni formato (con unità di conteggio) | Wizard | (4.4) |
| Tipo operazione Produzione o Imballo di ogni formato | Wizard | (4.4) |
| Rotta di ogni formato con le sue regole | Wizard | (4.4) |
| Distinte per variante e formato | **A mano** | Produzione → Distinte base (4.5) |
| Rotta sulla riga dell'ordine di vendita | Utente, a ogni ordine | Ordine di vendita (5.1) |

## 4. Configurazione, passo per passo

### 4.1 Anagrafica imballaggi

**Impostazioni** (*Inventario → Impostazioni*): attivare **Ubicazioni di magazzino**, **Percorsi multi-step** e **Colli**.

**Unità di misura.** Su ogni prodotto confezionato, le unità di vendita:

| Unità | Riferita a | Fattore | Tipologia collo |
|---|---|---|---|
| Sacco 10kg / 20kg / 25kg | kg (o t) | 10 / 20 / 25 | — |
| Big Bag 1000kg / 1200kg / 1500kg | kg (o t) | 1000 / 1200 / 1500 | facoltativa |
| Pallet 1500kg - 20kg x 75 | **Sacco 20kg** | 75 | Pallet 1500kg |
| Pallet 1500kg - 25kg x 60 | **Sacco 25kg** | 60 | Pallet 1500kg |

Regole che il modulo dà per scontate:

- un pallet è riferito **al suo sacco**, non al kg: è da lì che il pulsante legge quanti sacchi vanno in un collo;
- un pallet ha la **Tipologia collo** valorizzata, altrimenti il pulsante non lo propone e il wizard formato si ferma.

**Tipologie collo** (*Inventario → Configurazione → Tipologie collo*): una per pallet fisico (es. *Pallet 1500kg*). La stessa tipologia può servire più confezioni (20 kg × 75 e 25 kg × 60). Se in futuro volete che la rotta si scelga da sola dall'unità della riga d'ordine, serve una tipologia per formato.

**Prodotti di imballo**: tipo *Beni*, **Traccia magazzino** attivo.

| Prodotto | Unità | Nota |
|---|---|---|
| Pedana 100x100 | Unità | |
| Film estensibile | kg | prodotto **distinto** dalla Bobina dei sacchi, per tenere separati i consumi |
| Cappuccio, angolari, etichette… | a scelta | se usati |
| Sacco plastica 10 / 20 / 25 kg | Unità | con la sua distinta **Kit** sulla Bobina (componente delle distinte sacco, 4.5) |

**Materiali per tipologia collo** (*Tipologia collo → scheda Materiali di imballo*), quantità **per singolo collo**:

| Tipologia collo | Materiale | Quantità per collo |
|---|---|---|
| Pallet 1500kg | Pedana 100x100 | 1 Unità |
| Pallet 1500kg | Film estensibile | dose da confermare, in kg |

Il pulsante Imballa moltiplica queste quantità per il numero di colli creati.

### 4.2 Struttura di magazzino (una volta)

| Cosa | Valori |
|---|---|
| Ubicazione `WH/Confezionato` | Interna, sotto il magazzino. Padre di tutti i formati e partenza delle consegne. |
| Tipo operazione **Prelievo confezionato** | Trasferimento interno; sezione *Imballo pallet (Alimac)*: **Convalida automatica** ✓ |
| Tipo operazione **Ordini di consegna** | Quello standard del magazzino; **Convalida automatica** spenta |

### 4.3 Installazione del modulo

1. Copiare il modulo nel repository Alimac e aggiornare l'elenco app.
2. Installare (o aggiornare) **Alimac - Imballo pallet da produzione**.
3. Verificare:
   - ubicazione **Consumo Imballi**: tipo *Produzione*, **senza ubicazione primaria** (su Odoo 19 le ubicazioni virtuali non hanno padre). Se esisteva già sotto *Inventory adjustment*, viene riusata: svuotare il padre a mano;
   - se c'erano le personalizzazioni Studio: sezione 8.

### 4.4 Formati: wizard *Configura formato confezionato*

*Inventario → Configurazione → Gestione magazzino → Configura formato confezionato* (Inventario / Amministratore).

Un lancio per formato: **prima tutti i formati di produzione, poi i pallet**, perché un pallet richiede il suo sacco già configurato.

| Campo | Cosa mettere | Proposto |
|---|---|---|
| Tipo di formato | *Formato di produzione* (sacco, big bag) o *Formato pallet* | — |
| Magazzino | WH | primo magazzino dell'azienda |
| Unità del formato | es. Sacco 25kg, oppure Pallet 1500kg - 25kg x 60 | — |
| Ubicazione confezionato | `WH/Confezionato` | l'ubicazione chiamata "Confezionato" del magazzino |
| Ubicazione componenti | `WH/Giacenza` | giacenza principale del magazzino |
| Tipo operazione prelievo | Prelievo confezionato | il tipo interno con *Convalida automatica* |
| Tipo operazione consegna | Ordini di consegna | consegne del magazzino |
| Ubicazione materiali di imballo (pallet) | `WH/Giacenza` | giacenza principale |
| Ubicazione di consumo imballi (pallet) | Consumo Imballi | Consumo Imballi |
| Nomi di ubicazione, tipo operazione, rotta, prefisso | modificabili | dal nome dell'unità |

Cosa crea:

| Formato | Ubicazione | Tipo operazione | Rotta |
|---|---|---|---|
| Produzione (es. Sacco 25kg) | `WH/Confezionato/Sacco 25kg`, unità di conteggio Sacco 25kg | *Produzione - Sacco 25kg*: copia del tipo produzione del magazzino, `WH/Giacenza` → ubicazione del formato | *Vendita confezionato Sacco 25kg*: Consegna ← Prelievo ← Produzione |
| Pallet (es. Pallet 1500kg - 25kg x 60) | `WH/Confezionato/Pallet 1500kg - 25kg x 60`, unità di conteggio il pallet | *Imballo Pallet…*: interno, ubicazione sacchi → ubicazione pallet, flag imballo, ubicazioni materiali e consumo | *Vendita confezionato Pallet…*: Consegna ← Prelievo ← Imballo ← Produzione sacchi |

Regole create nelle rotte (tutte con **Ubicazione di destinazione presa dalla regola**):

| Regola | Metodo di fornitura |
|---|---|
| Consegna (`WH/Confezionato` → Clienti) | Attiva un'altra regola |
| Prelievo (formato → `WH/Confezionato`) | Preleva da giacenza, se non disponibile attiva un'altra regola |
| Imballo (sacchi → pallet) | Preleva da giacenza, se non disponibile attiva un'altra regola |
| Produzione | — |

Le rotte sono selezionabili sulla **riga dell'ordine di vendita**, non sul prodotto.

Se un elemento esiste già, il wizard lo **riusa senza modificarlo**:

| Elemento | Come lo riconosce |
|---|---|
| Ubicazione | sotto l'ubicazione confezionato, con la stessa **unità di conteggio**; altrimenti direttamente sotto, con lo **stesso nome** |
| Tipo operazione | stesso tipo (produzione / interno con flag imballo) e stessa **ubicazione di destinazione** predefinita |
| Rotta | stesso **nome** |
| Sacco di un pallet | ubicazione con l'unità di conteggio del sacco **e** tipo operazione di produzione che ci arriva |

Unica modifica su record esistenti: imposta l'unità di conteggio su un'ubicazione riusata che non ce l'ha, e attiva la *Convalida automatica* sul tipo operazione di prelievo indicato.

L'**anteprima** in fondo al wizard dice, prima di confermare, cosa verrà creato e cosa riusato. Attenzione ai nomi: un'ubicazione esistente chiamata `Sacco25kg` senza unità di conteggio **non** viene riconosciuta dal nome proposto *Sacco 25kg*. In quel caso impostare prima l'unità di conteggio sull'ubicazione, oppure correggere il nome nel wizard.

Il wizard **non** crea unità, tipologie collo, prodotti, materiali né distinte.

### 4.5 Distinte

Una distinta per **ogni variante confezionato** e **ogni formato sacco o big bag** venduto. I pallet non hanno distinta: nascono dall'Imballo.

| Campo | Valore |
|---|---|
| Prodotto / Variante | variante *confezionato* |
| Quantità | 1 nell'unità del formato (es. 1 Sacco 25kg) |
| Tipologia | Produzione del prodotto |
| Componente | variante *sfuso* della stessa granulometria, quantità = peso del formato (es. 25 kg) |
| Componente | Sacco plastica del formato, 1 Unità (big bag: il big bag vuoto, se gestito) |
| Scheda Varie → Tipo di operazione | *Produzione - <formato>* creato dal wizard |

Perché il tipo di operazione è obbligatorio: su Odoo 19 la regola di produzione cerca prima una distinta con il **suo** tipo operazione. Se non la trova, prende una distinta qualsiasi del prodotto, e il tipo operazione della distinta ha la precedenza su quello della regola. Con la distinta di un altro formato l'MO esce sbagliato (es. ordine di 3 Sacco 25kg → MO di 3,75 Sacco 20kg). Il modulo lo segnala con un avviso sull'MO.

### 4.6 Riepilogo dei flag sui tipi operazione

Sezione *Imballo pallet (Alimac)*, visibile sui trasferimenti interni:

| Tipo operazione | Operazione di imballo pallet | Convalida automatica | Ubicazione materiali | Ubicazione di consumo |
|---|---|---|---|---|
| Imballo (uno per formato pallet) | ✓ | ✗ | `WH/Giacenza` | Consumo Imballi |
| Prelievo confezionato | ✗ | ✓ | — | — |
| Ordini di consegna | ✗ | ✗ | — | — |
| Produzione (uno per formato) | — | — | — | — |

### 4.7 Unità di conteggio delle ubicazioni

*Ubicazione → Unità di conteggio*: valorizzata dal wizard sulle ubicazioni dei formati. Per altre ubicazioni si imposta a mano. Determina la colonna **N** delle giacenze: es. *Sacco 20kg* su `Sacco20kg` mostra il numero di sacchi.

### 4.8 Permessi

| Funzione | Gruppo |
|---|---|
| Pulsante Imballa | Produzione / Utente |
| Wizard formato | Inventario / Amministratore |
| Materiali per tipologia collo (modifica) | Inventario / Amministratore |
| Colonne colli nelle giacenze | impostazione *Colli* attiva |

## 5. Utilizzo

### 5.1 Ordine di vendita

Sulla riga: prodotto variante *confezionato*, unità del formato (es. Pallet 1500kg - 25kg x 60) e **rotta del formato** (es. *Vendita confezionato Pallet 1500kg - 25kg x 60*). Alla conferma Odoo crea l'MO in sacchi e i trasferimenti della rotta.

### 5.2 Ordine di produzione

- Il campo **Imballaggio** mostra cosa è stato ordinato (es. *2 Pallet 1500kg - 25kg x 60*); c'è anche nell'elenco degli MO.
- Se compare l'**avviso giallo** ("l'ordine chiede … ma la produzione è in …"), manca la distinta del formato o non ha il tipo di operazione giusto (4.5). Va corretto prima di produrre.
- Si chiude l'MO dichiarando i sacchi realmente prodotti, anche più del previsto.

### 5.3 Pulsante Imballa

Visibile sull'MO **completato**. Il wizard propone:

| Campo | Da dove |
|---|---|
| Trasferimento di imballo | quello della rotta dell'ordine; vuoto se l'MO è per magazzino (ne verrà creato uno) |
| Confezione, tipologia collo | dall'unità della riga d'ordine |
| Quantità per collo | dall'unità pallet (es. 60 sacchi), modificabile (es. 15 per pallet corti) |
| Quantità da imballare | quanto richiesto dall'ordine; per magazzino, solo i colli completi |
| Colli da creare, quantità ultimo collo | calcolati |
| Materiali di imballo da scaricare | dalla tipologia collo × numero di colli, modificabili |

**Imballa** crea i colli, scarica i materiali da `WH/Giacenza` verso *Consumo Imballi* e convalida l'Imballo; poi il prelievo si chiude da solo.

Pulsanti intelligenti:

- MO → **Imballi**: i trasferimenti di imballo;
- Imballo → **Materiali imballo**: gli scarichi di pedane e film.

### 5.4 Giacenze

*Inventario → Report → Giacenze*:

| Colonna | Significato |
|---|---|
| N | quantità nell'unità di conteggio dell'ubicazione (sacchi, pallet), sommabile |
| Tipologia collo | tipologia del collo che contiene la merce; *Raggruppa per → Tipologia collo* |
| N colli | numero di colli, sommabile |

## 6. Comportamento nei vari casi

| Caso | Risultato |
|---|---|
| Produzione **superiore** all'ordine | Imballa la quantità ordinata; l'eccedenza resta nell'ubicazione sacchi. |
| Produzione **inferiore** all'ordine | Imballa quanto prodotto (es. colli 75 + 65); il resto dell'Imballo va in **backorder**. Il prelievo resta in attesa, perché la merce non è tutta disponibile. |
| Quantità da imballare ridotta a mano | Imballa quella; il resto va in backorder e si imballa ripremendo Imballa. |
| MO per magazzino | Crea un Imballo con i soli colli completi; i sacchi restanti rimangono in ubicazione. |
| Stesso prodotto in pallet e in sacchi nello stesso ordine | Odoo unisce le richieste in **un solo MO** (es. 123 sacchi), che mostra *2 Pallet… + 3 Sacco 25kg*. Imballa imballa i 120 del pallet, i 3 sacchi vanno al loro prelievo. Un solo WH/OUT. |
| Due prodotti nello stesso Imballo | Ogni MO imballa il suo prodotto; l'altro passa in backorder e lo trova il suo MO. |
| Formato ordinato senza distinta | Avviso sull'MO (4.5). |
| Sacchi o pallet già a stock | Le regole *Preleva da giacenza, se non disponibile attiva un'altra regola* li usano prima di produrre. |
| MO non completato | Il pulsante Imballa non è visibile. |

Nota Odoo 19: le regole *Preleva da giacenza, se non disponibile attiva un'altra regola* non collegano i movimenti tra loro (MO → Imballo → Prelievo). Il modulo ritrova Imballo e Prelievo dal **riferimento comune** (l'ordine di vendita), dal prodotto e dall'ubicazione, quindi funziona con entrambi i metodi di fornitura.

## 7. Cosa dipende da un nome

Imballaggi, quantità e materiali vengono sempre dalla configurazione. Gli unici riferimenti per nome sono questi:

| Dove | Nome | Effetto |
|---|---|---|
| Installazione | *Consumo Imballi* | Cercata per nome (maiuscole/minuscole indifferenti), creata se manca. Dopo conta solo il campo sul tipo operazione: si può rinominare. |
| Wizard formato | ubicazione *Confezionato* | Solo come **proposta** dell'ubicazione confezionato; modificabile. |
| Wizard formato | "Vendita confezionato …", "Produzione - …", "Imballo …" | Solo **nomi proposti**, modificabili. Il nome della rotta serve a riconoscere una rotta già esistente. |
| Migrazione Studio | campo `x_studio_imballo_1`, regola *Validazione prelievo confezionato da produzione*, tipi operazione *Prelievo confezionato* | Una volta sola, all'installazione o all'aggiornamento; se non li trova non fa nulla. |

## 8. Migrazione dalle personalizzazioni Studio

All'installazione, e all'aggiornamento da versioni precedenti:

| Studio | Diventa | Cosa fa il modulo |
|---|---|---|
| Campo `x_studio_imballo_1` su Ubicazione (*Imballo*) | **Unità di conteggio** | Copia il valore su ogni ubicazione (la prima unità, se erano più di una) |
| Campo `x_studio_n` su Giacenza (*N*) | Colonna **N** | Calcolata dal modulo, nessun dato da copiare |
| Regola di automazione *Validazione prelievo confezionato da produzione* | **Convalida automatica** | Attiva il flag sui tipi operazione *Prelievo confezionato* e **archivia** la regola |

Dopo aver verificato che tutto funzioni, a mano:

1. In Studio, togliere dalle viste ed eliminare `x_studio_n` (Giacenza) e `x_studio_imballo_1` (Ubicazione). Fino ad allora nel report giacenze ci sono due colonne "N".
2. Eliminare la regola archiviata (*Impostazioni → Tecnico → Automazione → Regole di automazione*, filtro Archiviati).
3. Archiviare tipi operazione, rotte e distinte dei pallet configurati a mano prima del modulo (es. *Produzione - Pallet150020x75*, distinte pallet con la pedana).
4. Riesportare le personalizzazioni Studio.

Gli altri campi Studio (Codice Gamma, Qtà TON, Peso, Effettuata da…) non riguardano questo modulo.

## 9. Limiti noti

- **N colli** è corretto se ogni collo contiene un solo prodotto e un solo lotto (caso Alimac).
- I prodotti tracciati a **lotti o seriali** non sono gestiti: Alimac non li usa sul confezionato.
- I materiali di imballo vengono scaricati **anche senza giacenza** (giacenza negativa), come concordato per la fase iniziale.
- Il costo dei materiali va all'ubicazione di consumo (su *Consumo Imballi* si può indicare un conto in *Costi di produzione*) e **non** entra nel valore del confezionato.
- Il pulsante Imballa non è nell'app **Shop Floor**: solo nel modulo dell'MO.
- Se sul tipo operazione Imballo ci sono **controlli qualità**, la convalida si ferma e il pulsante dà errore senza scaricare nulla.
- Con la stessa tipologia collo per più formati pallet, la rotta va scelta sulla riga d'ordine (non può derivare dalla tipologia collo).

## 10. Note tecniche

| Elemento | Dettaglio |
|---|---|
| `alimac.package.type.material` | nuovo modello: materiali per collo di una `stock.package.type` |
| `stock.package.type` | `alimac_material_line_ids` |
| `stock.picking.type` | `alimac_is_pallet_packing`, `alimac_material_location_id`, `alimac_consumption_location_id`, `alimac_auto_validate` |
| `stock.location` | `alimac_count_uom_id`; `_alimac_get_consumption_location()` |
| `stock.quant` | `alimac_count_qty` (N), `alimac_package_type_id`, `alimac_package_count` (memorizzati, sommabili) |
| `stock.picking` | `alimac_production_id` (imballi creati per MO a magazzino), `alimac_material_move_ids` |
| `stock.move` | `alimac_packing_picking_id`; override di `_action_done` per la convalida automatica |
| `mrp.production` | pulsanti *Imballa* e *Imballi*; `alimac_sale_packaging_summary`, `alimac_sale_uom_id`, `alimac_sale_uom_qty`, `alimac_packaging_mismatch` |
| `alimac.pallet.packing.wizard` | wizard Imballa (+ righe materiali) |
| `alimac.packaging.format.wizard` | wizard Configura formato confezionato |
| `hooks.py`, `migrations/` | migrazione Studio, creazione Consumo Imballi (idempotenti) |

Scelte implementative:

- colli creati con il metodo standard `stock.move.line._put_in_pack(package_type_id=…)`, spezzando le righe prenotate per collo;
- scarico materiali sullo schema di `stock.scrap` (movimento con riga valorizzata, poi `_action_done`);
- convalida con `button_validate` e `skip_backorder`: se si imballa meno della richiesta, il backorder nasce senza domande;
- convalida automatica solo se il trasferimento è **tutto disponibile**, con i colli interi (`_check_entire_pack`);
- contesto ripulito (`clean_context`) prima di generare movimenti, per non propagare `default_production_id`;
- Imballo e Prelievo ritrovati dalla catena dei movimenti oppure dal riferimento comune, prodotto e ubicazione (necessario con le regole *mts_else_mto* di Odoo 19).

## 11. Test

```bash
odoo-bin -d <db> -u alimac_mrp_imballo_pallet --test-tags=/alimac_mrp_imballo_pallet --stop-after-init
```

18 test, eseguiti su Odoo 19 Community.

**Pulsante Imballa e campi** (`test_pallet_packing.py`):

1. Sovraproduzione (160 sacchi su 150): 2 colli, 10 sacchi restano, materiali scaricati, campi giacenza.
2. MO per magazzino: Imballo con soli colli completi.
3. Quantità per collo personalizzata (2 pallet da 15 sacchi).
4. Imballo parziale manuale: backorder e secondo imballo dal backorder.
5. Pulsante bloccato su MO non completato.
6. Sottoproduzione (140 su 150): colli 75 + 65, backorder.
7. Rotta pallet: prelievo convalidato in automatico, colli interi a destinazione.
8. Rotta sacchi: prelievo convalidato in automatico dopo l'MO.
9. Colonna N con l'unità di conteggio.
10. Migrazione da Studio.
11. Due prodotti nello stesso Imballo.
12. Imballaggio ordinato sull'MO.
13. Avviso di formato non corrispondente.

**Flusso completo dall'ordine di vendita** (`test_format_wizard.py`, rotte create dal wizard):

1. Configurazione dei formati e rilancio senza duplicati.
2. Ordine 2 pallet 25x60: MO 120 sacchi, prodotti 130, Imballa, prelievo automatico, consegna con 2 colli, 10 sacchi restano.
3. Ordine 3 sacchi: prelievo automatico dopo l'MO.
4. Consumo Imballi creata all'installazione.
5. Ordine misto pallet + sacchi dello stesso prodotto: MO unico, un solo WH/OUT.
