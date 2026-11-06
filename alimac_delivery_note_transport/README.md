# Alimac Delivery Note Transport

## Descrizione

Modulo per sostituire il sistema legacy "Gestra" (2001) nella registrazione e rendicontazione dei costi di trasporto sui DDT (Documenti di Trasporto) in porto franco.

## Scopo

Gestra era un piccolo gestionale interno usato per:
- Registrare per ogni spedizione: data, trasportatore, cliente/destinazione, tipo mezzo, costo
- Produrre stampe mensili di rendiconto per vettore e destinazione
- Calcolare tonnellate trasportate e spesa totale

Questo modulo integra la stessa funzionalità direttamente in Odoo, collegandosi ai DDT esistenti.

## Funzionalità Principali

### 1. Campi su DDT (stock.delivery.note)

#### transport_cost (Monetary)
- Costo del trasporto pagato al vettore
- **Editabile anche dopo la conferma del DDT**
- Tracciato (tracking=True)
- In valuta della società

#### transport_tons (Float, computed, stored)
- Tonnellaggio totale trasportato
- Calcolato automaticamente dai movimenti di stock (stock.move)
- Usa `product_qty` che è già in UdM base (tonnellate)
- Solo movimenti nello stato 'done'
- Precisione: 3 decimali

#### destination_partner_id (Many2one, computed, stored)
- Partner di destinazione
- `partner_shipping_id` se valorizzato, altrimenti `partner_id`
- Usato per raggruppamenti e report

### 2. Condizioni di Trasporto

Il modulo crea/assegna XML ID a tre record di `stock.picking.transport.condition`:

- `transport_condition_porto_franco` - "Porto franco"
- `transport_condition_porto_assegnato` - "Porto assegnato"  
- `transport_condition_con_addebito` - "Con addebito in fattura"

**Importante**: Gli XML ID permettono di filtrare per condizione senza usare nomi traducibili.

### 3. Viste Estese

#### Form View
Campi aggiunti dopo `carrier_id`:
- Transport Cost (editabile)
- Transport Tonnage (readonly, calcolato)

#### Tree View
Colonne aggiuntive (opzionali):
- Transport Cost (con sum)
- Transport Tonnage (con sum)
- Destination Partner

#### Search View
**Nuovi filtri:**
- "Porto Franco" - filtra per condizione porto franco
- "Active DDT" - esclude bozze e annullati (state not in ('draft', 'cancel'))
- "With Transport Cost" - solo DDT con costo > 0

**Nuovi raggruppamenti:**
- Carrier (Vettore)
- Destination (Destinazione)
- Transport Condition (Condizione trasporto)
- Month (Mese)

### 4. Analisi Pivot

Azione dedicata: **Transport Analysis**

- Vista pivot con misure: Count, Tonnage, Cost
- Raggruppamento predefinito: Carrier → Destination
- Filtri predefiniti: Porto Franco + Active DDT
- Viste disponibili: Pivot, Graph, Tree, Form

Menu: **Delivery Notes → Transport Analysis**

### 5. Report Mensile (Wizard)

Sostituisce la stampa di Gestra.

**Parametri:**
- Mese (required)
- Anno (required)
- Vettore (opzionale - se vuoto include tutti)
- Condizioni trasporto (default: Porto Franco)

**Filtro DDT:**
```python
date nel mese selezionato
state not in ('draft', 'cancel')
carrier_id valorizzato
transport_condition_id nelle condizioni selezionate
```

**Output PDF:**

Per ogni vettore:
- Tabella con destinazioni (nome, città, viaggi, tonnellate, costo)
- Subtotale vettore
- Grand total finale

Esempio:
```
Vettore X
  Pisa          | 3 viaggi | 15.500 t | 300,00 €
  Firenze       | 2 viaggi |  8.200 t | 180,00 €
  Subtotale X   | 5 viaggi | 23.700 t | 480,00 €

TOTALE GENERALE | 5 viaggi | 23.700 t | 480,00 €
```

Menu: **Delivery Notes → Monthly Report**

## Calcolo Tonnellate

Il calcolo è **automatico** e si basa sui movimenti di stock:

```python
for picking in ddt.picking_ids:
    for move in picking.move_ids.filtered(lambda m: m.state == 'done'):
        total_tons += move.product_qty  # già in UdM base
```

**Note:**
- `product_qty` è sempre in UdM base del prodotto (tonnellata)
- Non serve conversione manuale
- Solo movimenti 'done' sono contati
- Aggiornamento automatico quando i picking cambiano

## Destinazione

La destinazione è determinata con questa logica:

```python
destination = partner_shipping_id or partner_id
```

**Snapshot città:**
La città viene letta da `partner.city` al momento della generazione del report.

**Nota:** Se serve uno snapshot fisso (città al momento della conferma DDT), aggiungere:
```python
dest_city = fields.Char(compute='_compute_dest_city', store=True)
```
Da decidere con il cliente (Cosimo).

## Differenze da Gestra

### Cosa Gestra faceva:
- Sistema separato, dati inseriti manualmente
- Nessun collegamento con DDT o fatture
- Solo stampe mensili
- Confronto manuale costo registrato vs fattura vettore

### Cosa fa questo modulo:
- ✅ Integrato con DDT esistenti
- ✅ Tonnellate calcolate automaticamente
- ✅ Analisi pivot real-time
- ✅ Filtri e raggruppamenti flessibili
- ✅ Report PDF identico a Gestra
- ❌ Confronto con fatture vettori (fuori perimetro - manuale)

## Utilizzo

### Processo Standard

1. **Creare/confermare DDT**
   - Selezionare vettore (carrier_id)
   - Selezionare condizione trasporto (es. "Porto franco")
   - Confermare il DDT

2. **Registrare costo trasporto**
   - Aprire il DDT (anche se già confermato)
   - Inserire il costo in "Transport Cost"
   - Salvare

3. **Verificare tonnellate**
   - Il campo "Transport Tonnage" si aggiorna automaticamente
   - Basato sui movimenti di stock completati

4. **Analizzare dati**
   - Menu: Transport Analysis
   - Vista pivot: vettori → destinazioni
   - Filtrare per mese, vettore, condizione

5. **Generare report mensile**
   - Menu: Monthly Report
   - Selezionare mese e anno
   - (Opzionale) Selezionare vettore specifico
   - Print Report
   - PDF generato con dettaglio vettore/destinazione

## Esempio d'Uso

**Scenario:** Rendiconto mensile Gennaio 2026 per tutti i vettori

1. Menu → Delivery Notes → Monthly Report
2. Month: January
3. Year: 2026
4. Carrier: (vuoto = tutti)
5. Transport Conditions: Porto Franco
6. Click "Print Report"

**Output:**
```
Monthly Transport Report - January 2026

Trasporti SpA
  Milano    | 12 viaggi | 108.000 t | 2.400,00 €
  Roma      |  8 viaggi |  64.000 t | 1.600,00 €
  Subtotale | 20 viaggi | 172.000 t | 4.000,00 €

Logistica SRL
  Napoli    |  5 viaggi |  45.000 t | 1.000,00 €
  Subtotale |  5 viaggi |  45.000 t | 1.000,00 €

GRAND TOTAL | 25 viaggi | 217.000 t | 5.000,00 €
```

## Fuori Perimetro

### Non Incluso in Questo Modulo

1. **Ricavo trasporto incorporato**
   - Gestito da `alimac_sale_transport`
   - Separazione materiale/trasporto su vendite "franco destino"

2. **Margine ricavo/costo trasporto**
   - Richiede modulo ponte (fase successiva)
   - Collegamento tra alimac_sale_transport e alimac_delivery_note_transport

3. **Confronto con fatture vettori**
   - Resta manuale
   - Possibile estensione futura: collegare transport_cost con fatture fornitore

4. **Tipi di mezzo**
   - Non registrato (era in Gestra)
   - Può essere aggiunto se richiesto dal cliente

## Dipendenze

- `l10n_it_delivery_note` - Modulo OCA per DDT italiani
- `delivery` - Gestione vettori (carrier)
- `stock` - Movimenti di magazzino

## Compatibilità

- Odoo 19 Enterprise/Community
- l10n_it_delivery_note (OCA)

## Note Tecniche

### product_qty vs product_uom_qty

- `product_qty`: quantità in UdM **base** (sempre tonnellate)
- `product_uom_qty`: quantità in UdM della riga (sacchi, pallet, ecc.)

Il modulo usa `product_qty` per evitare conversioni.

### Editable After Confirmation

Il campo `transport_cost` è editabile anche dopo conferma DDT perché:
- I costi spesso arrivano dopo la spedizione
- l10n_it_delivery_note rende molti campi readonly dopo conferma
- Il nostro campo non è in quella lista readonly

### _read_group vs read_group

In Odoo 19 c'è `_read_group` (nuovo) che restituisce liste di dict.

Il wizard usa:
```python
DeliveryNote._read_group(
    domain,
    ['carrier_id'],
    ['carrier_id', 'transport_cost:sum', 'transport_tons:sum', 'id:count']
)
```

### Snapshot Città

**Opzione 1 (implementata):** Città letta al momento del report
- Pro: Sempre aggiornata
- Contro: Cambio indirizzo partner altera lo storico

**Opzione 2 (non implementata):** Snapshot alla conferma DDT
```python
dest_city = fields.Char(
    compute='_compute_dest_city',
    store=True
)

@api.depends('destination_partner_id', 'state')
def _compute_dest_city(self):
    for note in self:
        if note.state not in ('draft', 'cancel'):
            note.dest_city = note.destination_partner_id.city
```
- Pro: Storico immutabile
- Contro: Campo ridondante

Da decidere con Cosimo.

## Testing

### Checklist di Test

- [ ] DDT con condizione "Porto franco" e vettore
- [ ] Inserire transport_cost su DDT confermato
- [ ] Verificare transport_tons calcolato correttamente
- [ ] Filtro "Porto Franco" funziona
- [ ] Filtro "Active DDT" esclude draft/cancel
- [ ] Raggruppamento per vettore
- [ ] Raggruppamento per destinazione
- [ ] Pivot view con misure corrette
- [ ] Report mensile con un vettore
- [ ] Report mensile con tutti i vettori
- [ ] Report mensile su mese senza dati
- [ ] PDF report leggibile e corretto
- [ ] Subtotali e grand total corretti

### Dati di Test

```python
# DDT 1: Vettore A, Destinazione Milano, 10t, 200€
# DDT 2: Vettore A, Destinazione Milano, 5t, 100€
# DDT 3: Vettore B, Destinazione Roma, 8t, 180€

Report atteso:
Vettore A
  Milano | 2 viaggi | 15.000 t | 300,00 €
  
Vettore B
  Roma   | 1 viaggio | 8.000 t | 180,00 €

TOTALE | 3 viaggi | 23.000 t | 480,00 €
```

## Supporto

Per problemi o domande: support@progresso.it

## Autore

**Progresso Srl**  
https://www.progresso.it

## Licenza

LGPL-3
