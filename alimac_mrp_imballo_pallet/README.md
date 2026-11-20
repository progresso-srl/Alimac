# Alimac – Imballo pallet da produzione

Modulo: `alimac_mrp_imballo_pallet` · Odoo 19.0 · Dipendenze: `mrp`

## A cosa serve

Alimac produce sempre in **sacchi**. I pallet (e gli altri colli) si fanno dopo, quando la produzione è finita, e la macchina spesso fa qualche sacco in più rispetto all'ordine.

Il modulo aggiunge il pulsante **Imballa** sull'ordine di produzione completato. Il pulsante:

1. divide i sacchi in **colli** secondo la confezione (es. *Pallet 1500kg - 20kg x 75* → 75 sacchi per collo);
2. crea i colli con la **tipologia collo** (es. *Pallet 1500kg*) sul trasferimento di imballo;
3. **scarica i materiali di imballo** configurati sulla tipologia collo (pedana, film, cappuccio…), moltiplicati per il numero di colli;
4. **convalida** il trasferimento di imballo.

I sacchi in più **non vengono toccati**: restano nell'ubicazione sacchi (es. `WH/Confezionato/Sacco20kg`) e sono disponibili per un imballo successivo.

Aggiunge inoltre alle giacenze i campi **Tipologia collo** e **N colli**, per leggere quanti pallet ci sono in ogni ubicazione.

## Flusso di riferimento

Rotta *Vendita confezionato pallet 1500 20-75*:

| Regola | Da → A | Tipo operazione |
|---|---|---|
| Consegna | `WH/Confezionato` → Clienti | Ordini di consegna |
| Prelievo | `Pallet 1500 - 20x75` → `WH/Confezionato` | Prelievo confezionato |
| **Imballo** | `Sacco20kg` → `Pallet 1500 - 20x75` | **Imballo 20x75** ← gestito dal pulsante |
| Produzione | → `Sacco20kg` | Produzione - Sacco20kg |

Esempio: ordine di 2 pallet (150 sacchi), la macchina ne fa 160.

- MO chiuso con 160 sacchi → tutti in `Sacco20kg`.
- **Imballa** → 2 colli da 75 sacchi in `Pallet 1500 - 20x75`, scarico di 2 pedane e 2 × film.
- 10 sacchi restano in `Sacco20kg`.

## Configurazione

### 1. Tipo di operazione di imballo
*Inventario → Configurazione → Tipi di operazione → Imballo 20x75*

- **Operazione di imballo pallet**: attivo.
- **Ubicazione materiali di imballo**: da dove si scaricano pedane e film (es. `WH/Giacenza`).
- **Ubicazione di consumo imballi**: ubicazione virtuale di destinazione dei materiali consumati (tipo *Produzione* o *Rettifica inventario*, es. `Virtual Locations/Consumo imballi`).
- Ubicazioni predefinite: origine `WH/Confezionato/Sacco20kg`, destinazione `WH/Confezionato/Pallet 1500 - 20x75`.

Il tipo di operazione deve essere di tipo *Trasferimento interno*. I campi compaiono nella scheda Generale, sezione *Imballo pallet (Alimac)*.

### 2. Materiali per tipologia collo
*Inventario → Configurazione → Tipologie collo → Pallet 1500kg → scheda Materiali di imballo*

Inserire i materiali **per singolo collo**, ad esempio:

| Materiale | Quantità per collo | Unità |
|---|---|---|
| Pallet in legno 100x100 | 1 | Unità |
| Film estensibile | 0,4 | kg |

La stessa tipologia collo può essere usata da più confezioni (20 kg × 75 e 25 kg × 60): i materiali sono quelli del pallet fisico.

### 3. Confezioni sul prodotto
Già presenti nella configurazione Alimac: le unità di imballaggio del prodotto (es. *Pallet 1500kg - 20kg x 75*, riferita a *Sacco 20kg* con fattore 75) devono avere la **Tipologia collo** valorizzata. Il pulsante propone solo le confezioni con tipologia collo.

### 4. Permessi
Il pulsante è visibile agli utenti **Produzione / Utente**. Per vedere le colonne dei colli nelle giacenze serve l'impostazione **Colli** attiva (*Inventario → Impostazioni*).

## Utilizzo

1. Chiudere l'MO dichiarando i sacchi realmente prodotti (anche più del previsto).
2. Premere **Imballa**.
3. Controllare il wizard:
   - **Trasferimento di imballo**: quello creato dalla rotta dell'ordine; se vuoto, ne verrà creato uno nuovo.
   - **Confezione** e **Tipologia collo**: proposte dall'unità della riga d'ordine.
   - **Quantità per collo**: 75 sacchi (modificabile, es. 15 per pallet "corti").
   - **Quantità da imballare**, **Colli da creare**, **Quantità ultimo collo**.
   - **Materiali di imballo da scaricare**: modificabili prima di confermare (es. film effettivamente usato).
4. **Imballa** → si apre il trasferimento di imballo convalidato, con i colli.

Dall'MO, il pulsante intelligente **Imballi** apre i trasferimenti di imballo collegati. Dal trasferimento di imballo, il pulsante **Materiali imballo** mostra gli scarichi di pedane e film.

## Comportamento nei vari casi

| Caso | Cosa fa il pulsante |
|---|---|
| MO da ordine, produzione **superiore** alla richiesta | Imballa la quantità richiesta; l'eccedenza resta in ubicazione sacchi. |
| MO da ordine, produzione **inferiore** alla richiesta | Imballa quanto prodotto (es. 75 + 65); il resto dell'imballo va in **backorder**. |
| Quantità da imballare ridotta a mano | Imballa la quantità indicata; il resto dell'imballo va in backorder e si può imballare premendo di nuovo **Imballa**. |
| MO **per magazzino** (nessun imballo collegato) | Crea un nuovo imballo con i soli **colli completi**; i sacchi restanti rimangono in ubicazione. |
| Pallet non standard (es. 30 sacchi in 2 pallet da 15) | Impostare *Quantità per collo* = 15: 2 colli, materiali per 2 pallet. |
| MO non completato | Il pulsante non è visibile; l'imballo richiede la produzione chiusa. |

## Giacenze: Tipologia collo e N colli

Sulle giacenze (report per ubicazione e rettifiche di inventario) sono disponibili:

- **Tipologia collo**: la tipologia del collo che contiene la merce (memorizzata, raggruppabile con il filtro *Raggruppa per → Tipologia collo*).
- **N colli**: 1 per ogni riga di giacenza dentro un collo, con totale nei raggruppamenti.

Raggruppando per ubicazione e prodotto si legge, ad esempio, *Granulato Nero Assoluto – Pallet 1500kg – 2 colli*.

## Limiti noti

- **N colli** è corretto se ogni collo contiene **un solo prodotto e un solo lotto** (caso Alimac). Un collo misto verrebbe contato più volte.
- I prodotti con **tracciabilità a lotti/seriali** non sono stati considerati: Alimac non li usa sul confezionato.
- I materiali di imballo vengono scaricati anche se non c'è giacenza (giacenza negativa), come concordato per la fase iniziale.
- Il costo dei materiali segue la valorizzazione standard di Odoo per i movimenti verso l'ubicazione di consumo scelta: **non** viene aggiunto al valore del prodotto confezionato.
- Il modulo non crea rotte né ubicazioni: vanno configurate come da tabella *Flusso di riferimento*.

## Note tecniche

| Elemento | Dettaglio |
|---|---|
| Nuovo modello | `alimac.package.type.material`: materiali per collo, collegati a `stock.package.type` |
| `stock.package.type` | `alimac_material_line_ids` |
| `stock.picking.type` | `alimac_is_pallet_packing`, `alimac_material_location_id`, `alimac_consumption_location_id` |
| `stock.picking` | `alimac_production_id` (imballi creati per MO a magazzino), `alimac_material_move_ids` |
| `stock.move` | `alimac_packing_picking_id`: lega lo scarico materiali all'imballo |
| `stock.quant` | `alimac_package_type_id` (related memorizzato), `alimac_package_count` (somma) |
| `mrp.production` | pulsante *Imballa*, pulsante intelligente *Imballi* |
| Wizard | `alimac.pallet.packing.wizard` + righe `alimac.pallet.packing.wizard.material` |

Scelte implementative:

- I colli si creano con il metodo standard `stock.move.line._put_in_pack(package_type_id=…)`; le righe prenotate vengono spezzate per collo.
- Lo scarico materiali segue lo schema di `stock.scrap` (movimento con riga già valorizzata, poi `_action_done`).
- La convalida usa `button_validate` con `skip_backorder`: se si imballa meno della richiesta, il backorder viene creato senza domande.
- Il contesto del wizard viene ripulito (`clean_context`) prima di generare movimenti, per non propagare `default_production_id` ai movimenti creati da Odoo.

## Test

```bash
odoo-bin -d <db> -u alimac_mrp_imballo_pallet --test-tags=/alimac_mrp_imballo_pallet --stop-after-init
```

Scenari coperti:

1. Imballo da rotta con sovraproduzione (160 sacchi su 150): 2 colli, 10 sacchi restano, materiali scaricati, campi giacenza valorizzati.
2. MO per magazzino: creazione dell'imballo con soli colli completi.
3. Quantità per collo personalizzata (2 pallet da 15 sacchi).
4. Imballo parziale manuale: backorder e secondo imballo dal backorder.
5. Pulsante bloccato su MO non completato.
6. Sottoproduzione (140 sacchi su 150): colli 75 + 65, backorder per il resto.

## Autore

Progresso Srl
