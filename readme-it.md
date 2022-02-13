# Doppler Shifter

Ho conseguito la patente di Radioamatore nel Febbraio 2021 (Grazie a Mauro IK1WUQ e i suoi video) e quando ho scoperto che c'erano dei satelliti radioamatoriali in orbita mi ha subito affascinato l'idea di poterli contattare e completare un QSO tramite essi.
Questo mi ha fatto entrare in un "tunnel" durato qualche mese che mi ha portato all ottenere tutto il necessario per una stazione portatile per contattare i satellit (FM o Lineari).
Uno dei componenti principali della stazione è quello che io ho nominato "doppler shifter" perchè permette di semplificare la gestione delle frequenze tenendo conto dell'effetto doppler (in inglese "Doppler Shift").
Doppler Shifter è uno strumento studiato per semplificare l'utilizzo dei satelliti radioamatoriali (sia lineari che FM) in modalità full-duplex.


## Funzionalità

- sincronizza il VFO di due radio (tramite controllo CAT) in base per l'utilizzo su i satelliti lineari invertenti (dove aumentando la frequenza di downlink la frequenza di uplink scende e viceversa) e gestisce in automatico il cambio di frequenza
- corregge automaticamente la frequenza in base all'effetto doppler
- imposta automaticamente la banda, il modo ed eventuali toni sub-audio (per i satelliti con transponder FM)
- data l'orario, la posizione e i TLE (two line element sets) di un satellite permette di visualizzare in tempo reale azimuth e elevazione
- invia la posizione del satellite ad un rotore per antenne per poterlo tracciare
- aggiorna automaticamente i TLE dal sito celestrak
- permette di avere una lista personalizzata dei satelliti e delle relative impostazioni e frequenze
- permette di salvare eventuali correzioni tra la frequenza di uplink e di downlink da utilizzare al prossimo passaggio
- utilizza il collegamento GPS (se è presente) per stabilire l'orario estatto e la posizione GPS. In caso non fosse disponibile viene utilizzata la posizione specificata nel file di configurazione.

Nonostante (quasi) tutte queste funzionalità siano già presenti in numerosi software per PC (come gpredict, satpc32, ecc) ho voluto costruire qualcosa che sia innanzitutto molto portatile (per questo un Raspberry Pi) e di facile utilizzo. 
Il software è scritto nel linguaggio di programmazione Python il che lo rende semplice da modificare e personalizzare e allo stesso tempo compatibile con quasi tutti i sistemi operativi e tipi di hardware.

## Requisiti

per poter funzionare sono necessari:

- un Raspberry Pi 3b o 4
- uno schermo [LCD](http://www.lcdwiki.com/3.5inch_RPi_Display) da 3.5" compatibile con [LCD-show](https://github.com/goodtft/LCD-show) o un computer 
- due radio (una per la ricezione e una per la trasmissione) controllabili tramite CAT e compatibili con il software [Hamlib](https://hamlib.github.io) e i relativi cavi di collegamento (il mio setup è un ICOM IC-705 per RX e un Yaesu FT-818ND per TX).
- un mouse con rotella e almeno 4 pulsanti (io utilizzo un [Logitech MX Anywhere 3](https://www.logitech.com/it-it/products/mice/mx-anywhere-3.html))
- un rotore per antenne compatibile con Hamlib (opzionale) 


![Raspberry Pi 4 con LCD montato ](./images/doppler_shifter_raspberry.jpg?raw=true)

## Installazione

per l'installazione seguire i passaggi elencati nel file [install-it.md](./install-it.md)

## Configurazione

E' necessario configurare alcune impostazioni nei seguenti file json presenti nella cartella **./config/**:

 ### config.json:
 - frequency_step: permette di impostare lo step utilizzato durante il cambio di frequenza della rotella del mouse
 - timezone: il vostro fuso orario
 - mouse_buttons: in questa sezione potete mappare le funzionalità del software ai bottoni del mouse (utilizzare la modalità di debug per visualizzare a quale numero corrispondono i bottoni)
 - rotator: configurazione del rotore (vedi Hamlib)
 - rigs: qui potete configurare varie configurazioni di radio diverse, selezionabili dal menu "rigs"
 - observer_conf: qui dovete impostare le vostre coordinate ed altitudine per rendere affidabile il calcolo della posizione del satellite
 - range1 e range2: qui potete impostare due fasce di gradi utilizzate dal controllo del rotore. Nel mio caso il mio rotore è posizionato sul balcone e posso solo tracciare satelliti che passano da i 350 a i 160 gradi della bussola.
 - sat_url: qui potete configurare la sorgente dei TLE. Ho usato celestrak perchè è quello più aggiornato.

### satlist.json
il file satlist.json contiene la lista dei satelliti. Ogni satellite dovrà contenere le seguenti informazioni:

- name: nome del satellite (dovrà combaciare con uno dei satelliti provenienti dal file contenente i TLE
- display_name: nome che sarà visualizzato nel programma
- up_start/center/end: inizio/centro/fine della banda passante del uplink del satellite
- down_start/center/end: inizio/centro/fine della banda passante del downlink del satellite
- inverting: se il satellite è invertente (non penso esistano più satelliti lineari non-invertenti)
- beacon: frequenza del beacon (se presente)
- saved_uplink_diff: sarà utilizzato nel futuro per salvare un eventuale differenza di shift tra l'uplink e il downlink



## utilizzo

una volta eseguito il software vi troverete davanti una schermata con diverse righe di informazioni e alcuni bottoni che abilitano delle funzionalità e aprono dei menù.

![schermata principale](./images/main_screen_istruzioni.png?raw=true)

La schermata principale permette di visualizzare le seguenti informazioni:

- riga 1: nome del satellite selezionato e frequenza del beacon
- riga 2: Azimuth e elevazione corrente - se i VFO sono bloccati
- riga 3 (uplink): frequenza richiesta - modo - stato della comunicazione con la radio
- riga 4 (uplink): frequenza con correzione dell'effetto doppler  - hertz di correzione per effetto doppler (aggiunti o sottratti)
- riga 5 (downlink): frequenza richiesta - modo - stato della comunicazione con la radio
- riga 6 (downlink): frequenza con correzione dell'effetto doppler  - hertz di correzione per effetto doppler (aggiunti o sottratti)
- riga 7 e 8: i due slider corrispondono alla posizione della frequenza rispetto alla banda passante del satellite (se lineare). Nel caso dei satelliti FM questo slider è disattivato e lo potete ignorare.

bottoni:

- Sats: porta al menù di selezione dei satelliti
- Radio: porta al menù di selezione delle readio
- Beacon: sintonizza la radio in rx sul beacon del satellite (di solito una trasmissione CW o telemetria digitale)
- Center: se si è spostati di frequenza con la rotella riporta al centro della banda passante del satellite
- Track: permette di attivare il tracking del rotore
- On/Off: permette di attivare o disabilitare il controllo della frequenza (è utile disattivarlo quando si vogliono cambiare delle impostazini sulla radio)
- Swap: scambia il ruolo delle radio (da tx->rx e viceversa)

### Menu Sats:
![sat_menu](./images/sat_menu.png?raw=true)

Premendo il bottone "Sats" nella schermata principale apparirà un menù che permetterà di cambiare satellite premendo sulle frecce a destra e a sinistra del nome. La lista dei satelliti è configurabile dal file satlist.json

Oltre alla scelta dei satelliti sono presenti:

- un orologio digitale per verificare che l'orario sia giusto
- il bottone "Return to Menu" per tornare alla schermata principale
- il bottone "Shutdown" uno per effettuare lo spegnimento del Raspberry Pi in modalità sicura(lancierà il comando "sudo shutdown -h now") 
- il bottone "Quit" per per chiudere il programma.

### Menu Radio
![radio_menu](./images/radio_menu.png?raw=true)

Nel menu radio è possibile selezionare le radio impostate nel file config.json (sotto la voce "rigs"). In automatico viene selezionata la prima radio presente nella lista come uplink e la seconda come downlink.

sono anche presenti due bottoni ("restart downlink rig" e "restart uplink rig") per riavviare rispettivamente i servizi rigctld di downlink e uplink. Quest è utile nel caso le radio vengano accese dopo il raspberry pi o se durante il funzionamento venisse staccato e riattacato il cavo USB.

il bottone start kappanhang lancia un comando per avviare [kappanhang](https://github.com/nonoo/kappanhang), un servizio che permette di creare una porta seriale "virtuale" tramite WiFi per il Icom IC-705.

