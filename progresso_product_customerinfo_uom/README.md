# Progresso - Prezzi cliente per unità di misura

## Problema

Con `product_customerinfo` (OCA) si possono inserire più prezzi per lo stesso
cliente e prodotto, ognuno con un'UdM diversa (es. pallet, big bag). Il modulo
OCA però ignora l'UdM: sull'ordine usa sempre una sola riga, la prima per
sequenza, quantità minima e **prezzo più basso**. Tutti gli imballi ricevono
così lo stesso prezzo.

## Cosa fa il modulo

Quando il prezzo viene calcolato con la regola di listino
*Prezzi del partner nella scheda prodotto*, la riga cliente è scelta in base
all'UdM della riga d'ordine:

1. riga cliente con la **stessa UdM** della riga d'ordine;
2. altrimenti riga cliente **generica**, nell'UdM del prodotto (es. tonnellata);
3. altrimenti nessuna: si usa il prezzo di vendita standard, mai il prezzo di
   un altro imballo.

A parità di UdM resta l'ordine del modulo OCA, e la riga sulla variante ha la
precedenza su quella sul modello prodotto.

Il prezzo in scheda cliente resta espresso nell'**UdM del prodotto** (€/t),
come nel modulo OCA; Odoo lo converte nell'UdM della riga.

## Esempio

Prodotto in tonnellate, cliente con tre righe in scheda prodotto:

| UdM riga cliente | Prezzo (€/t) | Riga ordine: 1 × | Prezzo unitario |
|---|---|---|---|
| Pallet 1500kg - 60x25kg | 95,00 | Pallet 1500kg | 142,50 |
| Big Bag 1500kg | 65,00 | Big Bag 1500kg | 97,50 |
| Big Bag 1000kg | 85,00 | Big Bag 1000kg | 85,00 |

## Configurazione

- Listino del cliente con **una sola regola** (globale o per categoria):
  *Formula*, basata su *Prezzi del partner nella scheda prodotto*.
  Non servono regole per singola variante o UdM.
- In scheda prodotto, sezione *Clienti*: una riga per imballo, con l'UdM
  dell'imballo e il prezzo a tonnellata.

## Limiti

- Codice/nome prodotto cliente e quantità minima proposta sulla riga d'ordine
  (`product_customerinfo_sale`) restano quelli del modulo OCA, non legati
  all'imballo.
- Date di validità della riga cliente non considerate (come nel modulo OCA).

## Dipendenze

- `product_customerinfo_sale` (OCA/sale-workflow), che dipende da
  `product_customerinfo` (OCA/product-attribute).
