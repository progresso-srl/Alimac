# Alimac - Tariffe trasporto per indirizzo di consegna

Il costo del trasporto dipende dall'indirizzo di consegna. Ogni indirizzo di
consegna ha la sua tariffa (€/t o €/viaggio) e l'ordine di vendita crea da solo
la riga trasporto.

Il modulo è indipendente da `alimac_sale_transport` (incorpora/scorpora) e non
lo richiede. Se è installato, la riga creata qui è quella che
"Incorpora trasporto" ripartisce sui prodotti.

## Configurazione

1. Prodotto **Trasporto**: tipo *Servizio*, UdM *Unità*, imposte uguali a quelle
   della merce. Con `alimac_sale_transport` installato va spuntato anche
   **Trasporto** (`is_transport`).
   - *Fatturazione: quantità consegnate* → si fattura il trasporto sulle
     tonnellate spedite (consigliato).
   - *Quantità ordinate* → si fattura sulle tonnellate ordinate.
2. **Vendite > Configurazione > Impostazioni > Spedizione > Trasporto da
   indirizzo di consegna**: scegliere il prodotto Trasporto.
3. Precisione decimale **Product Unit** (Impostazioni > Tecnico > Precisione
   decimale): con 2 decimali le tonnellate della riga trasporto si arrotondano
   a 10 kg (es. 3 sacchi da 25 kg = 0,075 t → 0,08 t). Con 3 decimali si
   arriva al kg.

## Tariffe

- Sul contatto di tipo **Consegna**, scheda **Tariffe trasporto** (anche nel
  popup aperto da "Contatti e indirizzi" del cliente). Sugli altri tipi di
  contatto la scheda non compare.
- **Vendite > Ordini > Tariffe trasporto**: tutte le tariffe in una lista
  modificabile, raggruppata per cliente, con filtro "Valide oggi", import ed
  export da Excel.
- **Vendite > Ordini > Indirizzi di consegna**: solo gli indirizzi di consegna,
  con la colonna *Tariffa attuale* e il filtro *Senza tariffa*.

Campi della tariffa:

| Campo | Note |
|---|---|
| Indirizzo di consegna | solo contatti di tipo Consegna |
| Magazzino/Stabilimento | facoltativo, è il magazzino di partenza dell'ordine. Vuoto = vale da qualsiasi magazzino; se esiste, vince la tariffa con il magazzino dell'ordine. Il campo compare solo quando esiste più di un magazzino attivo (Odoo attiva e disattiva da solo il gruppo Magazzini multipli): con un solo magazzino non si vede. Con più magazzini e una regola unica basta lasciarlo vuoto |
| Modalità | €/t oppure €/viaggio |
| Tariffa | importo |
| Valida dal / al | facoltative. Per cambiare tariffa si chiude la vecchia con "Valida al" e se ne crea una nuova |

Non sono ammesse due tariffe valide nello stesso periodo per lo stesso
indirizzo e magazzino.

## Sull'ordine di vendita

Sotto l'indirizzo di consegna compare **Tariffa trasporto**, ma solo se
l'indirizzo di consegna è un contatto di tipo **Consegna**. Se l'indirizzo di
consegna è il cliente stesso (o un contatto di altro tipo) non compare nulla e
non si crea nessuna riga: lì si usa, se serve, la spedizione nativa di Odoo
(**Aggiungi spedizione**).


- è proposta dalla tariffa dell'indirizzo valida alla data dell'ordine;
- è modificabile sul singolo ordine. La conferma non la riporta al valore
  dell'indirizzo; il pulsante ↻ la rilegge dall'indirizzo;
- con €/viaggio compare **N. viaggi** (default 1);
- se l'indirizzo di consegna non ha una tariffa valida alla data dell'ordine
  compare un avviso. Scrivendo la tariffa sull'ordine, il pulsante **Salva
  sull'indirizzo** la salva per i prossimi ordini (valida da oggi;
  l'eventuale tariffa precedente viene chiusa a ieri). Lo stesso pulsante
  compare quando si modifica a mano la tariffa proposta.

La **riga trasporto** si crea e si aggiorna da sola quando si salva l'ordine,
cambiano le righe merce, l'indirizzo, il magazzino o la tariffa, e alla
conferma:

- €/t: quantità = tonnellate delle righe merce (sacchi, big bag e pallet
  convertiti tramite l'unità; per prodotti non a peso si usa il peso del
  prodotto), UdM tonnellate;
- €/viaggio: quantità = N. viaggi;
- prezzo = tariffa dell'ordine. "Aggiorna prezzi" e i listini non lo
  modificano;
- descrizione: "Trasporto – via, città (25,00 €/t)".

Nessuna riga se:

- la tariffa è 0. Per togliere il trasporto da un ordine basta azzerare la
  tariffa: eliminare la riga a mano non basta, perché si ricrea al salvataggio
  successivo;
- con `l10n_it_delivery_note`, la condizione di trasporto è **Porto
  assegnato**;
- non è configurato il prodotto Trasporto.

Su ordine confermato Odoo non permette di eliminare righe: in quel caso la
riga trasporto va a quantità 0. Una riga trasporto già fatturata non viene più
toccata.

**Quantità consegnata**: alla convalida di consegne e resi la riga trasporto
prende le tonnellate effettivamente spedite (€/t), oppure i viaggi appena parte
la prima consegna (€/viaggio).

## Con alimac_sale_transport (franco destino)

1. L'ordine crea la riga trasporto dalla tariffa dell'indirizzo.
2. **Incorpora trasporto**: la riga viene ripartita sui prodotti come oggi.
3. Finché il trasporto è incorporato, tariffa e riga trasporto sono bloccate.
   Per cambiarle: **Scorpora**, modificare, poi incorporare di nuovo.

Con porto franco "con addebito in fattura" non si incorpora: la riga trasporto
resta visibile e va in fattura.

## Note tecniche

- Modelli: `sale.address.transport.rate`; campi aggiunti su `res.partner`,
  `res.company`, `sale.order`, `sale.order.line` (`is_address_transport`).
- La riga trasporto è esclusa da `_compute_price_unit`, `_compute_discount` e
  `_get_update_prices_lines`.
- I controlli su `l10n_it_delivery_note` (porto assegnato) e su
  `alimac_sale_transport` (incorporato) sono "morbidi": si attivano solo se i
  rispettivi campi esistono, quindi nessuna dipendenza.
- Test: `--test-tags=/alimac_sale_address_transport`.
