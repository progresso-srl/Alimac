# Alimac - Base (ex personalizzazioni Studio)

Modulo che sostituisce le personalizzazioni Studio di Alimac ancora utili:
solo campi e viste sui moduli standard, nessuna logica di business.

Le **tonnellate** (Qtà t sulle righe d'ordine, Totale tonnellate, tonnellate del
trasferimento e del DDT, stampe) sono in `alimac_delivery_note_transport`, con la
regola di conversione unica.

## 1. Cosa fa

| Funzione | Dove | Campo |
|---|---|---|
| Codice Gamma | Variante; sul modello solo se c'è una sola variante | `product.product.alimac_gamma_code` |
| Pulsante Listino prodotti | Contatto | `res.partner.alimac_customerinfo_count` |
| Menu Righe ordine di vendita (pivot; Qtà t si aggiunge da Misure) | Vendite > Report | — |
| Menu Listino prodotti-clienti | Vendite > Prodotti | — |
| Colonne: UdM in Analisi vendite; UdM imballo, Codice Gamma, peso negli elenchi prodotti; tipo operazione negli elenchi distinte | | — |

## 2. Codice Gamma: un solo campo

In Studio c'erano due campi: *Codice Gamma* sul modello (`x_studio_codice_gamma`)
e *Sku Gamma* sulla variante (`x_studio_codice_gamma_1`). Ora il dato è uno,
sulla variante, e il modello lo mostra e lo modifica quando c'è una sola
variante, come il Riferimento interno. Si cerca anche dalla ricerca prodotti.
Non viene copiato duplicando il prodotto.

## 3. Installazione: migrazione da Studio

L'installazione (`hooks.py`):

1. copia *Sku Gamma* nel nuovo Codice Gamma della variante;
2. per i modelli con **una sola variante** e Sku vuoto copia il *Codice Gamma*
   del modello;
3. i modelli con **più varianti** e Codice Gamma sul modello **non** vengono
   toccati: sono elencati nel log (`Codice Gamma sul modello con più
   varianti`) e il dato resta nel campo Studio. Vanno sistemati a mano;
4. **disattiva** (non cancella) le viste e i menu Studio sostituiti, compresi
   quelli di giacenze/ubicazioni già sostituiti da `alimac_mrp_imballo_pallet`.
   Le viste Studio delle tonnellate (ordine e trasferimento) le disattiva
   `alimac_delivery_note_transport`.

## 4. Revisione delle personalizzazioni Studio

| Studio | Esito |
|---|---|
| `product.template.x_studio_codice_gamma` (Codice Gamma) | Unificato in `alimac_gamma_code` |
| `product.product.x_studio_codice_gamma_1` (Sku Gamma) | Unificato in `alimac_gamma_code` |
| `product.product.x_studio_related_field_56t_1k4dh3faj` (Quantità = qtà distinta) | Eliminabile: non è in nessuna vista |
| `stock.location.x_studio_imballo_1` (Imballo) | Già in `alimac_mrp_imballo_pallet` (`alimac_count_uom_id`) |
| `stock.quant.x_studio_n` (N) | Già in `alimac_mrp_imballo_pallet` (`alimac_count_qty`) |
| `sale.order.line.x_studio_qta_peso` (Qtà TON) | `alimac_delivery_note_transport`: `alimac_qty_tons`, calcolo corretto |
| `sale.order.x_studio_totale_tonnellate` (Totale tonnellate) | `alimac_delivery_note_transport`: `alimac_total_tons` |
| `stock.picking.x_studio_totale_tonnellate` e `x_studio_pesoton` (entrambi "Peso(ton)") | `alimac_delivery_note_transport`: un solo campo `alimac_tons`; nella scheda DDT del trasferimento le tonnellate del DDT |
| `res.partner.x_partner_id_product_customerinfo_count` + azione "Nuovo pulsante" | Pulsante Listino prodotti |
| `<header>` vuoto nella scheda contatto | Eliminato |
| Menu Righe ordine di vendita, Listino prodotti-clienti | Nel modulo |
| Colonne UdM (Analisi vendite), UdM imballo, peso, tipo operazione distinte | Nel modulo |
| `mrp.production.x_studio_effettuata_da` (Effettuata da: Operatore 1 / Operatore 2) | **Resta in Studio**: valori segnaposto, da definire (elenco fisso, dipendenti, utenti) prima di portarlo in codice |

## 5. Dopo la verifica: pulizia Studio (a mano)

Da *Impostazioni > Tecnico* (modalità sviluppatore), in quest'ordine:

1. **Viste** (`ir.ui.view`, filtro "Odoo Studio:"): eliminare le viste
   disattivate dall'installazione;
2. **Azioni** "Righe ordine di vendita", "Listino prodotti-clienti", "Nuovo
   pulsante" (modello `product.customerinfo` / `sale.order.line`) e i due menu Studio disattivati;
3. **Campi** (`ir.model.fields`, nome che inizia per `x_studio_` o
   `x_partner_id_product_customerinfo_count`): eliminare quelli della tabella
   sopra, tranne `x_studio_effettuata_da`. Per `x_studio_codice_gamma`
   controllare prima il log del punto 3.3.

Prima di eliminare i campi, verificare che importazioni/esportazioni salvate e
filtri preferiti non li usino: vanno rifatti sul nuovo campo **Codice Gamma**.
