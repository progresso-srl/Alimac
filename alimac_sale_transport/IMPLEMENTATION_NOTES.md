# Implementation Notes - alimac_sale_transport

## Struttura Modulo Creato

```
alimac_sale_transport/
├── __init__.py
├── __manifest__.py
├── README.md
├── IMPLEMENTATION_NOTES.md (questo file)
├── models/
│   ├── __init__.py
│   ├── product_product.py
│   ├── sale_order.py
│   ├── sale_order_line.py
│   ├── account_move_line.py
│   └── decimal_precision.py
├── views/
│   ├── product_product_views.xml
│   ├── sale_order_views.xml
│   └── account_move_views.xml
├── report/
│   ├── sale_report_templates.xml
│   └── invoice_report_templates.xml
└── security/
    └── ir.model.access.csv
```

## Implementazione Completata

### ✅ Models

#### 1. product_product.py
- Campo `is_transport` (Boolean) per identificare i prodotti trasporto

#### 2. sale_order.py
- Campo `transport_incorporated` (Boolean, readonly)
- Metodi helper: `_get_transport_lines()`, `_get_product_lines()`
- Metodo `_get_tonnage_for_line()` per conversione UoM → tonnellate
- Metodo `_compute_transport_distribution()` per calcolo ripartizione proporzionale
- Action `action_incorporate_transport()` con validazioni complete
- Action `action_uncorporate_transport()` per ripristino
- Override `copy_data()` per gestire duplicazione coerente

**Validazioni implementate:**
- Presenza righe trasporto
- Presenza righe con tonnellate convertibili
- Uniformità imposte tra prodotti e trasporto
- Blocco se esistono fatture registrate

#### 3. sale_order_line.py
- Campi: `transport_reference_amount`, `material_price_unit`, `transport_price_unit`
- Campi computed (stored): `material_amount`, `transport_amount`
- Override `write()` per bloccare modifiche quando incorporato
- Override `create()` per impedire aggiunta righe quando incorporato
- Override `_prepare_invoice_line()` per copiare campi su fattura
- Override `_compute_qty_to_invoice()` per escludere righe trasporto incorporate
- Metodo `_get_invoiceable_lines()` per filtrare righe trasporto

**Formula calcolo:**
```python
material_amount = material_price_unit × qty × (1 - discount/100)
transport_amount = price_subtotal - material_amount
```

#### 4. account_move_line.py
- Stessi campi di sale_order_line per tracciamento su fattura
- Calcolo material_amount e transport_amount
- Supporto note di credito (valori negativi)

#### 5. decimal_precision.py
- Post-init hook per aggiornare precisione "Product Price" a 4 decimali
- Crea la precisione se non esiste

### ✅ Views

#### 1. product_product_views.xml
- Campo `is_transport` aggiunto a product.template e product.product

#### 2. sale_order_views.xml
**Form view:**
- Pulsanti "Incorporate Transport" e "Uncorporate Transport" nel header
- Alert informativo quando trasporto incorporato
- Colonne opzionali: Material Price, Transport Quota, Material Amount, Transport Amount
- Campo Transport Reference sulla riga trasporto
- Decorazione `decoration-muted` per righe trasporto incorporate (grigie)

**Tree view:**
- Campo `transport_incorporated` opzionale

**Visibilità pulsanti:**
```python
Incorporate: invisible="transport_incorporated or invoice_count > 0"
Uncorporate: invisible="not transport_incorporated or invoice_count > 0"
```

#### 3. account_move_views.xml
- Colonne opzionali su invoice_line_ids per Material/Transport tracking

### ✅ Reports

#### 1. sale_report_templates.xml
- Override del template `report_saleorder_document`
- Filtro per nascondere righe trasporto incorporate al cliente
- Lambda: `not (l.product_id.is_transport and l.order_id.transport_incorporated and l.transport_reference_amount > 0 and l.price_unit == 0)`

#### 2. invoice_report_templates.xml
- Template placeholder (le righe trasporto non arrivano nemmeno in fattura)

### ✅ Security

#### ir.model.access.csv
- Accessi base per sales_team.group_sale_salesman
- Read/write su product, sale.order, sale.order.line
- Read-only su account.move.line

## Logica di Incorporazione

### Fase 1: Validazione
1. Verifica presenza righe trasporto
2. Verifica non già incorporato
3. Verifica assenza fatture registrate
4. Verifica presenza righe con tonnellate

### Fase 2: Calcolo Tonnellate
```python
for line in product_lines:
    tonnage = line.product_uom._compute_quantity(
        line.product_uom_qty, 
        line.product_id.uom_id  # base UoM = tonnellate
    )
```

### Fase 3: Distribuzione
```python
total_transport = sum(transport_lines.price_subtotal)
total_tonnage = sum(line_tonnages)

for line_id, tonnage in line_tonnage.items():
    distribution[line_id] = (tonnage / total_tonnage) * total_transport
```

### Fase 4: Aggiornamento Prezzi
```python
material_price_unit = current_price_unit  # salva
transport_per_unit = transport_quota / (qty * (1 - discount/100))
new_price_unit = material_price_unit + transport_per_unit
```

### Fase 5: Azzeramento Riga Trasporto
```python
transport_line.transport_reference_amount = transport_line.price_subtotal
transport_line.price_unit = 0.0
```

### Fase 6: Lock
```python
order.transport_incorporated = True
# Le righe diventano non modificabili via write() e create()
```

## Gestione Fatturazione

### Sale Order → Invoice
1. `_prepare_invoice_line()` copia material_price_unit e transport_price_unit
2. `_get_invoiceable_lines()` esclude righe trasporto incorporate
3. Righe trasporto hanno `qty_to_invoice = 0`
4. **Risultato**: La fattura contiene solo righe prodotto con prezzi incorporati

### Consegne Parziali
- Il trasporto scala proporzionalmente
- Se ordinate 10t ma consegnate 5t, il trasporto si dimezza
- Questo è il **comportamento voluto** per Alimac

### Note di Credito
- I campi vengono copiati normalmente
- Gli importi diventano negativi automaticamente
- material_amount e transport_amount: negativi

## Edge Cases Gestiti

### 1. Duplicazione Ordine
- ✅ Campo `transport_incorporated` copiato (copy=True)
- ✅ Campi material/transport copiati (copy=True)
- ✅ Stato coerente: incorporato → prezzi già incorporati
- ✅ NO rischio doppia incorporazione

### 2. Annullamento/Ritorno in Bozza
- ✅ I pulsanti sono nascosti se ci sono fatture (invoice_count > 0)
- ✅ Lo stato incorporato persiste (scorporare manualmente se necessario)

### 3. Righe senza Tonnellate
- ✅ Escluse dalla ripartizione (servizi, sacchi vuoti, ecc.)
- ✅ Non causano errori
- ✅ Solo le righe convertibili partecipano

### 4. Imposte Diverse
- ✅ Validazione bloccante se prodotti e trasporto hanno imposte diverse
- ✅ Messaggio errore chiaro

### 5. Sconto di Riga
- ✅ Formula corretta: `transport_per_unit / (1 - discount/100)`
- ✅ Lo sconto NON erode il trasporto
- ✅ material_amount e transport_amount: somma = imponibile sempre

## Punti di Attenzione per Testing

### 1. Precisione Decimale
- [ ] Verificare che Product Price abbia 4 decimali dopo installazione
- [ ] Testare con prezzi come 83,3333 €/t (esempio GRBC1)
- [ ] Controllare che residui siano minimi (< 0,05 €)

### 2. Conversione UoM
- [ ] Testare con sacchi, pallet, tonnellate
- [ ] Verificare che UoM non convertibili siano escluse
- [ ] Controllare precision su uom_id

### 3. FatturaPA (l10n_it_edi)
- [ ] Verificare che PrezzoUnitario esporti 4 decimali
- [ ] Controllare che totali fattura siano corretti
- [ ] Testare con consegne parziali

### 4. Interfaccia Utente
- [ ] Pulsanti visibili/nascosti correttamente
- [ ] Alert informativo appare quando incorporato
- [ ] Righe trasporto in grigio quando incorporate
- [ ] Colonne opzionali mostrano valori corretti

### 5. Customer-Facing Documents
- [ ] PDF preventivo: riga trasporto nascosta
- [ ] PDF conferma: riga trasporto nascosta
- [ ] Portale cliente: riga trasporto nascosta
- [ ] Fattura: riga trasporto NON presente
- [ ] Email: riga trasporto nascosta

### 6. Validazioni
- [ ] Errore se manca riga trasporto
- [ ] Errore se mancano tonnellate
- [ ] Errore se imposte diverse
- [ ] Errore se fattura già registrata
- [ ] Blocco modifica righe quando incorporato
- [ ] Blocco aggiunta righe quando incorporato

## Possibili Estensioni Future

### 1. Report SQL (sale.report, account.invoice.report)
Estendere le viste per aggiungere colonne:
```sql
SUM(sol.material_amount) as material_revenue,
SUM(sol.transport_amount) as transport_revenue
```

### 2. Separazione Contabile
Se richiesto dall'amministrazione:
- Account separato per ricavo trasporto
- Split automatico in contabilità analitica

### 3. Configurazione per Cliente
- Checkbox su partner per "Sempre franco destino"
- Incorporazione automatica alla conferma

### 4. Vettori e Costi
- Collegamento con alimac_delivery_note_transport (fase successiva)
- Calcolo margine ricavo/costo trasporto

### 5. Prezzi Dinamici Trasporto
- Calcolo automatico trasporto in base a distanza/peso
- Integrazione con API vettori

## Note per Deployment

### Installazione
```bash
# Aggiungere il modulo alla lista
# Aggiornare la lista moduli
# Installare alimac_sale_transport
```

### Post-Installazione
1. Il post_init_hook aggiorna automaticamente la precisione
2. Creare un prodotto "Trasporto" e flaggare `is_transport = True`
3. Formare gli utenti sull'uso dei pulsanti

### Migration da Ordini Esistenti
- Gli ordini esistenti non sono incorporati (transport_incorporated = False)
- I campi material/transport sono a 0 (va bene)
- Nessuna migrazione dati necessaria

### Backup Consigliato
Prima dell'installazione:
1. Backup database
2. Test su ambiente di staging
3. Verificare tutti i casi d'uso

## Conclusioni

Il modulo `alimac_sale_transport` è completo e pronto per il testing. 

**Implementati:**
- ✅ Tutti i modelli e campi richiesti
- ✅ Logica di incorporazione/scorporazione
- ✅ Ripartizione proporzionale per tonnellate
- ✅ Blocco modifiche quando incorporato
- ✅ Gestione fatturazione con esclusione righe trasporto
- ✅ Viste backend con colonne aggiuntive
- ✅ Nascondi righe trasporto da cliente
- ✅ Validazioni complete
- ✅ Gestione edge cases
- ✅ Precisione decimale 4 cifre
- ✅ Documentazione completa

**Da fare (fase successiva):**
- Report SQL estesi (sale.report, account.invoice.report)
- Testing completo su ambiente di staging
- Formazione utenti
- Eventuale modulo ponte per margini (alimac_delivery_note_transport)

---

**Data implementazione:** 22/10/2026  
**Versione Odoo:** 19 Enterprise  
**Autore:** Progresso Srl
