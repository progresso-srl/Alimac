# Alimac Sale Transport

## Descrizione

Modulo per gestire le vendite "franco destino" in Alimac. Il cliente vede un unico prezzo per prodotto (materiale + trasporto incorporato), mentre internamente il sistema traccia separatamente il prezzo del materiale e la quota di trasporto per le statistiche e i report.

## Funzionalità Principali

### 1. Identificazione Prodotto Trasporto
- Campo `is_transport` sul prodotto per identificare i prodotti di tipo "Trasporto"
- Visibile nella scheda prodotto

### 2. Incorporazione/Scorporazione Trasporto
Due pulsanti sull'ordine di vendita:

- **"Incorpora trasporto"**: 
  - Visibile quando esiste almeno una riga trasporto
  - L'ordine non è già incorporato
  - Non ci sono fatture registrate
  - Salva il prezzo materiale originale
  - Ripartisce il trasporto sulle righe in proporzione alle tonnellate
  - Porta la riga trasporto a 0 conservando l'importo di riferimento
  - Blocca le righe da modifica

- **"Scorpora trasporto"**: 
  - Ripristina i prezzi originali e la riga trasporto
  - Sblocca le righe per la modifica
  - Non disponibile se ci sono fatture registrate

### 3. Ripartizione Proporzionale

La ripartizione del trasporto avviene in base alle tonnellate:

```
Esempio:
- GRBC1: 9 t × 70 €/t = 630 € + 120 € trasporto = 750 € (83,3333 €/t)
- CIBC715: 4,5 t × 124 €/t = 558 € + 60 € trasporto = 618 € (137,3333 €/t)
- Trasporto: 0 € (riferimento: 180 €)
Totale: 1.368 €
```

**Formula ripartizione:**
- Quota di riga = trasporto × (tonnellate riga / tonnellate totali)
- Quota per unità = quota di riga / quantità riga
- Prezzo incorporato = prezzo materiale + quota per unità

### 4. Campi Aggiunti

#### Product (product.product)
- `is_transport`: Boolean - Identifica il prodotto trasporto

#### Sale Order (sale.order)
- `transport_incorporated`: Boolean (readonly) - Stato incorporazione

#### Sale Order Line (sale.order.line)
- `transport_reference_amount`: Monetary - Importo trasporto di riferimento (solo riga trasporto)
- `material_price_unit`: Float - Prezzo materiale per unità
- `transport_price_unit`: Float - Quota trasporto per unità
- `material_amount`: Monetary (computed, stored) - Importo materiale
- `transport_amount`: Monetary (computed, stored) - Importo trasporto

#### Account Move Line (account.move.line)
- `material_price_unit`: Float - Prezzo materiale per unità
- `transport_price_unit`: Float - Quota trasporto per unità
- `material_amount`: Monetary (computed, stored) - Importo materiale
- `transport_amount`: Monetary (computed, stored) - Importo trasporto

### 5. Calcolo Importi

```python
material_amount = material_price_unit × quantità × (1 - sconto%)
transport_amount = imponibile - material_amount
```

Con questa definizione:
- Materiale + trasporto = imponibile (sempre)
- Lo sconto non erode il trasporto
- Funziona anche con le note di credito (valori negativi)

### 6. Fatturazione

- Le righe trasporto incorporate (prezzo 0, reference amount > 0) **NON** vengono fatturate
- I campi material_price_unit e transport_price_unit vengono copiati sulle righe fattura
- Per consegne parziali, il ricavo trasporto scala proporzionalmente alle tonnellate effettive
- Le note di credito copiano i campi con segno negativo

### 7. Viste e Report

#### Backend (Operatore)
- Colonne opzionali "Material Price", "Transport Quota", "Material Amount", "Transport Amount"
- Righe trasporto incorporate mostrate in grigio con importo di riferimento
- Alert informativo quando il trasporto è incorporato
- Righe bloccate (non modificabili/aggiungibili) quando incorporato

#### Customer-Facing (Cliente)
Le righe trasporto incorporate sono **nascoste** in:
- PDF preventivo
- PDF conferma d'ordine
- Fattura (non vengono nemmeno create)
- Portale cliente
- Email

Il cliente vede solo:
- Righe prodotto con prezzo incorporato (materiale + trasporto)
- Totale ordine corretto

### 8. Precisione Decimale

Il modulo aggiorna automaticamente la precisione "Product Price" a **4 decimali** (se inferiore) tramite un post_init_hook. Questo è necessario per:
- Calcoli accurati della ripartizione trasporto
- Evitare discrepanze nei totali
- Compatibilità con FatturaPA (fino a 8 decimali supportati)

**Nota**: La precisione è globale e può influenzare listini e altre viste.

### 9. Validazioni e Controlli

Il modulo previene errori bloccando operazioni non valide:

- ❌ Incorporazione senza righe trasporto
- ❌ Incorporazione senza righe con tonnellate convertibili
- ❌ Incorporazione con imposte diverse tra prodotti e trasporto
- ❌ Incorporazione se esistono fatture registrate
- ❌ Scorporazione se esistono fatture registrate
- ❌ Modifica righe quando trasporto è incorporato
- ❌ Aggiunta righe quando trasporto è incorporato

### 10. Duplicazione Ordini

Quando si duplica un ordine:
- Lo stato `transport_incorporated` viene mantenuto
- Tutti i campi (material_price_unit, transport_price_unit, ecc.) vengono copiati
- La copia è **coerente**: se incorporato, i prezzi sono già incorporati
- **Non** si corre il rischio di doppia incorporazione

### 11. Conversione Unità di Misura

Il modulo converte automaticamente:
- Sacchi → Tonnellate
- Pallet → Tonnellate
- Altre UoM → Tonnellate (se convertibili)

Righe non convertibili (es. servizi) sono escluse dalla ripartizione.

## Utilizzo

### Processo Standard

1. **Creare ordine di vendita**
   - Aggiungere righe prodotto con prezzi materiale
   - Aggiungere una riga "Trasporto" con importo totale (es. 180 €)

2. **Incorporare trasporto**
   - Cliccare il pulsante "Incorporate Transport"
   - Il sistema:
     - Calcola tonnellate per ogni riga
     - Ripartisce proporzionalmente
     - Aggiorna i prezzi
     - Azzera la riga trasporto
     - Blocca le modifiche

3. **Inviare al cliente**
   - Il cliente vede solo prodotti con prezzo a destino
   - La riga trasporto NON compare

4. **Consegna e fatturazione**
   - La fattura include solo righe prodotto
   - I campi material/transport vengono copiati
   - Le statistiche mostrano la separazione

5. **(Opzionale) Scorporare**
   - Prima della fatturazione si può scorporare per modifiche
   - Cliccare "Uncorporate Transport"
   - I prezzi originali vengono ripristinati

## Dipendenze

- `sale_management`
- `account`
- `l10n_it_edi` (per FatturaPA)
- `uom` (per conversione unità di misura)

## Compatibilità

- Odoo 19 Enterprise

## Limitazioni e Note

1. **Dopo fatturazione**: I pulsanti incorpora/scorpora sono nascosti e disabilitati
2. **Precisione globale**: L'aumento a 4 decimali è globale (influenza tutto il sistema)
3. **Conversione UoM**: Le righe devono essere convertibili in tonnellate
4. **Imposte uniformi**: Tutti i prodotti e il trasporto devono avere le stesse imposte
5. **Consegne parziali**: Il trasporto scala proporzionalmente (comportamento voluto)

## Report e Statistiche

I report `sale.report` e `account.invoice.report` possono essere estesi per includere misure:
- Ricavo materiale (material_amount)
- Ricavo trasporto (transport_amount)

*Nota: Questa estensione va implementata estendendo le viste SQL.*

## Contabilità

La separazione materiale/trasporto è **solo statistica**. In contabilità si registra un unico ricavo.

*Confermare con l'amministrazione se necessaria separazione contabile.*

## Supporto

Per problemi o domande: support@progresso.it

## Autore

**Progresso Srl**  
https://www.progresso.it

## Licenza

LGPL-3
