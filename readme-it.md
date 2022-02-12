# Doppler Shifter


## funzionalità
Doppler Shifter è uno strumento studiato per semplificare l'utilizzo dei satelliti radioamatoriali (sia lineari che FM) in modalità full-duplex e possiede le seguenti funzionalità:

- sincronizza il VFO di due radio (tramite controllo CAT) in base per l'utilizzo su i satelliti lineari invertenti (dove aumentando la frequenza di downlink la frequenza di uplink scende e viceversa) e gestisce in automatico il cambio di frequenza
- corregge automaticamente la frequenza in base all'effetto doppler
- imposta automaticamente la banda, il modo ed eventuali toni sub-audio (per i satelliti con transponder FM)
- data l'orario, la posizione e i TLE (two line element sets) di un satellite permette di visualizzare in tempo reale azimuth e elevazione
- invia la posizione del satellite ad un rotore per antenne per poterlo tracciare
- aggiorna automaticamente i TLE dal sito celestrak
- permette di avere una lista personalizzata dei satelliti e delle relative impostazioni e frequenze

Nonostante (quasi) tutte queste funzionalità siano già presenti in numerosi software per pc (come gpredict, satpc32, ecc) ho voluto costruire qualcosa che sia portatile e di facile utilizzo. Il software utilizza il linguaggio di programmazione Python il che lo rende semplice da modificare e personalizzare e compatibile con molti sistemi operativi e tipi di hardware.

## requisiti

per poter funzionare sono necessari:

- un Raspberry Pi 3b o 4
- uno schermo [LCD](http://www.lcdwiki.com/3.5inch_RPi_Display) da 3.5" compatibile con [LCD-show](https://github.com/goodtft/LCD-show) o un computer 
- due radio (una per la ricezione e una per la trasmissione) controllabili tramite CAT e compatibili con il software [Hamlib](https://hamlib.github.io) e i relativi cavi di collegamento (il mio setup è un ICOM IC-705 per RX e un Yaesu FT-818ND per TX).
- un mouse con rotella e almeno 4 pulsanti (io utilizzo un [Logitech MX Anywhere 3](https://www.logitech.com/it-it/products/mice/mx-anywhere-3.html))
- un rotore per antenne compatibile con Hamlib (opzionale) 

## installazione

per l'installazione seguire i passaggi elencati nel file install.md

## configurazione

configurare le vostre impostazioni nei seguenti file json presenti nella cartella *config*:

 ### config.json:
 - frequency_step: permette di impostare lo step utilizzato durante il cambio di frequenza della rotella del mouse
 - timezone: il vostro fuso orario
 - mouse_buttons: in questa sezione potete mappare le funzionalità del software ai bottoni del mouse (utilizzare la modalità di debug per visualizzare a quale numero corrispondono i bottoni)
 - rotator: configurazione del rotore (vedi Hamlib)
 - rigs: qui potete configurare varie configurazioni di radio diverse, selezionabili dal menu "rigs"
 - observer_conf: qui dovete impostare le vostre coordinate ed altitudine per rendere affidabile il calcolo della posizione del satellite
 - range1 e range2: qui potete impostare due fasce di gradi utilizzate dal controllo del rotore. Nel mio caso il mio rotore è posizionato sul balcone e posso solo tracciare satelliti che passano da i 350 a i 160 gradi della bussola.
 - sat_url: qui potete configurare la sorgente dei TLE. Ho usato celestrak perchè è quello più aggiornato.

## utilizzo

una volta eseguito il software vi troverete davanti una schermata con diverse righe di informazioni e alcuni bottoni che abilitano delle funzionalità e aprono dei menù.

![main_screen](./images/main_screen.png?raw=true)

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