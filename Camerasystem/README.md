# Camerasystem
Camerasystem for UiS Aerospace phoenix 2

System consists of:
 - 3 Cameranodes based on RPI Zero 2W
 - 1 Cameracentral RPI 5B

Cameranodes communicates with Cameracentral using ethernet over USB.

# Cammeranodes
## Flashing 
RPI IMAGER:
- RPI zero 2W
- Raspbian 64bit
- Hostname: CamNodeX
- Username: cameranodeX
- Passord: Aerospacesensor
- Enable ssh
- Add a wifi ssid and password. We used hotspot on our phone as the wifi. This makes the setup process much easier.

Before removing SD-card, open the disk in the file system: and do following changes.
- /boot/config.txt: Add "dtoverlay=dwc2" under the [ALL] section.
- /boot/cmdline.txt: Add "modules-load=dwc2,g_ether g_ether.host_addr=02:11:22:33:44:11 g_ether.dev_addr=02:11:22:33:44:01" after rootwait. BUT CHANGE THE MAC ADRESS TO MAKE IT UNIQE.


## After flashing
- Put SD-card in the RPI zero and power it up. Acces the node by using SSH on a personal computer connected to the same wifi/hotspot configured earlier.
- Set up the following
```
sudo nmcli connection add type ethernet ifname usb0 con-name usb0 ip4 192.168.1.10/24
sudo nmcli connection modify usb0 ipv4.method manual
sudo nmcli connection modify usb0 connection.autoconnect yes
sudo nmcli connection up usb0
```

## Watchdog script for noder
- Vil reboote etter XX minutter dersom den ikke får forbindelse til Cameracentral
- 

### Setup
- Endre batchscriptet watchdog.sh. Endre ip adresse og path til å matche noden.
- Gjør batchscript kjørbart ved å kjøre terminalkommando: ```chmod +x ~/camerasystem_node/watchdog.sh```
- Lag service-fil (starter ved oppstart): ```sudo nano /etc/systemd/system/watchdog.service```
- Lim inn dette, OG ENDRE path til riktig nodenummer (cameranode1..2..3):
- 

```
[Unit]
Description=Connection Watchdog
After=network-online.target
Wants=network-online.target

[Service]
ExecStart=/home/camerasystem_node/cameranode1/watchdog.sh
Restart=always
RestartSec=5
User=root

[Install]
WantedBy=multi-user.target
```

- lagre og kjør dette i terminal:
```
sudo systemctl daemon-reexec
sudo systemctl daemon-reload
sudo systemctl enable watchdog
```
- Watchdog.sh scriptet skal nå kjøre etter reboot
- Du kan teste om den fungerer (uten å reboote) ved å kjøre:
```
sudo systemctl start watchdog
systemctl status watchdog
journalctl -u watchdog -f
```

