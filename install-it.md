# configurazione hardware
1. collegare lo schermo LCD Touchscreen al Raspberry Pi and installare il driver compatibile. Nel mio caso è [LCD-show](https://github.com/goodtft/LCD-show)
2. collegare le radio tramite cavo CAT/USB
3. collegare un mouse tramite cavo o Bluetooth

# configurazione software
verificata sull'ultima versione di Raspbian attualmente presente (13/2/2022), sia 32bit che 64bit.

- installare i seguenti pacchetti 
    ```
    sudo apt-get install git python3-pip swig automake libtool -y
    ```
- clonare il repository di Hamlib 
    ```
    git clone https://github.com/Hamlib/Hamlib.git
    ```
- entrare nella cartella di Hamlib 
    ```
    cd Hamlib
    ```
- eseguire i seguenti comandi:
    ```
    ./bootstrap
    ./configure --with-python-binding PYTHON=$(which python3)
    make -j4 && sudo make install
    sudo ldconfig
- tornare alla cartella precedente
    ```
    cd ..
    ```
- clonare il repository di Doppler Shifter
    ```
    git clone https://github.com/giordyb/doppler_shifter.git
    ```
- entrare nella cartella di doppler_shifter 
    ```
    cd ../doppler_shifter
    ```
- installare le librerie Python richieste
    ```
    pip3 install -r requirements.txt
    ```
- copiare il file pre-configurato **99-serial-usb.rules** in /etc/udev/rules.d/ (solo se usate le stesse mie radio) 
    ```
    sudo cp 99-serial-usb.rules /etc/udev/rules.d/
    ```
- copiare i file *.service* nella cartella */etc/systemd/system/* Questi file sono necessari per configurare il servizio "rigctld" che controlla le radio. Per ulteriori informazioni fate riferimento a [rigctld](https://www.mankier.com/1/rigctld).
    ```
    sudo cp systemd/*.service /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable rigup
    sudo systemctl enable rigdown
    sudo systemctl start rigup
    sudo systemctl start rigdown
    ```
- modificare i file in "config/config.json" in base alle vostre preferenze. 

- a questo punto potete provare a lanciare il programma
    ```
    python3 doppler_shifter.py
    ```
- se tutto funziona correttamente potete copiare il file .desktop nella cartella */usr/share/applications/* per create un icona che permetterà il lancio del programma dal menu del Raspberry Pi
    ```
    cp doppler_shifter.desktop ~/.local/share/applications
    ```
- se avete un Icom IC-705 potete configurare il GPS utilizzando questa [guida](http://www.w1hkj.com/W3YJ/Pi_IC-705_GPS.pdf)