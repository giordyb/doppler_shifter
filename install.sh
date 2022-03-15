sudo apt-get install git python3-pip swig automake libtool -y
git clone https://github.com/Hamlib/Hamlib.git
git clone https://github.com/giordyb/doppler_shifter.git
cd Hamlib
./bootstrap
./configure --with-python-binding PYTHON=$(which python3)
make -j4 && sudo make install
sudo ldconfig
cd ../doppler_shifter
pip3 install -r requirements.txt
sudo cp 99-serial-usb.rules /etc/udev/rules.d/
sudo cp systemd/*.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable rigup
sudo systemctl enable rigdown
sudo systemctl enable rotator
