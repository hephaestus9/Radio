Radio
=====

Upcycled Radio 
Project Page: [Radio] (http://hackaday.io/project/1251-radio)
>Flash Ubuntu to eMMC
>Login: ubuntu
>Password: temppwd
 
sudo passwd ubuntu
>password: temppwd
>enter new password
>enter new password
 
sudo passwd root
>enter new password
>enter new password
 
nano /etc/rc.local
>add this line before "exit 0" 

ntpdate pool.ntp.org

>save & exit
 
sudo reboot
 
date
>time stamp should be in UTC time
 
apt-get update && apt-get upgrade -y
apt-get install alsa gstreamer0.10-plugins* python-gst0.10 build-essential python-dev python-setuptools python-pip python-smbus
 
>set autologin **You are required to be logged in as root for the BBIO to gain access to the ADC**
nano /etc/init/tty1.conf
 
>replace -> exec /sbin/getty -8 38400 tty1
>with -> #exec /sbin/getty -8 38400 tty1
>        exec /bin/login -f root < /dev/tty1 > /dev/tty1 2>&1
>save & exit
 
easy_install -U distribute
pip install Adafruit_BBIO
python -c "import Adafruit_BBIO.GPIO as GPIO; print GPIO"
 
>#you should see this or similar:
>\<module 'Adafruit_BBIO.GPIO' from '/usr/local/lib/python2.7/dist-packages/Adafruit_BBIO/GPIO.so'\>
 
pip install flask
pip install apscheduler
 
>edit /etc/network/interfaces
>remove comments for "WiFi Example" and enter ssid and password for your network
>save changes & exit
 
>reboot and disconnect ethernet cable
 
apt-get install xfce4 xorg synaptic pithos
 
startxfce4
 
>start pithos and get it working with your usb sound card, once that is working close it and go to the terminal 


># If you are using an realtek usb wifi adapter following are the instructions I had to follow to get it working:
>Grab the modified driver from here:
---

wget https://realtek-8188cus-wireless-drivers-3444749-ubuntu-1304.googlecode.com/files/rtl8192cu-tjp-dkms_1.6_all.deb)

>Find out your current kernel:
---

uname -a

>For me:
---

Linux arm 3.8.13-bone40

>Grab the kernel headers:
---

wget http://rcn-ee.net/deb/raring-armhf/v3.8.13-bone40/linux-headers-3.8.13-bone40_1.0raring_armhf.deb)

>Install those headers:
---

dpkg -i linux-headers-3.8.13-bone40_1.0raring_armhf.deb

>Install the dkms package and all its dependencies:
---

apt-get install dkms

>Install the rtl8192cu-tjp-dkms_1.6_all.deb package. It will fail, don't worry. We installing it for the source files!
---

dpkg -i rtl8192cu-tjp-dkms_1.6_all.deb

>Notice, we need arch armv7l. We'll fix the missing arch files.
---

ln -s /usr/src/linux-headers-3.8.13-bone40/arch/arm /usr/src/linux-headers-3.8.13-bone40/arch/armv7l

>Fix a problem with the timex.h header
---

vim /usr/src/linux-headers-3.8.13-bone40/arch/armv7l/include/asm/timex.h

>change line 18 from

"#include \<mach/timex.h\>"

>to

"#include \</usr/src/linux-headers-3.8.13-bone40/arch/arm/include/asm/timex.h\>"

>Run make to build the driver

cd /usr/src/rtl8192cu-tjp-1.6
---
make

>Copy the new module in to the kernel modules directory
---

cp 8192cu.ko /lib/modules/3.8.13-bone40/kernel/drivers/net/wireless/

>Update the module deps
---

depmod

>Blacklist the native drivers.
---

vim /etc/modprobe.d/blacklist.conf

>add this to the end:
---

```
# Blacklist native RealTek 8188CUs drivers
blacklist rtl8192cu
blacklist rtl8192c_common
blacklist rtlwifi
```

>If this was successful you should not have any trouble resolving a network address, and the wifi will stay connected.  Additionally, the light on the card should not be constantly lit but rather flashing to indicate traffic.

>edit \etc\network\interfaces

```
# This file describes the network interfaces available on your system
# and how to activate them. For more information, see interfaces(5).

# The loopback network interface
auto lo
iface lo inet loopback

# The primary network interface
auto eth0
iface eth0 inet dhcp
# Example to keep MAC address between reboots
#hwaddress ether DE:AD:BE:EF:CA:FE

# WiFi Example
auto wlan0
iface wlan0 inet dhcp
    wpa-ssid "YOUR_SSID"
    wpa-psk  "YOUR_PASSWORD"
    


# Ethernet/RNDIS gadget (g_ether)
# ... or on host side, usbnet and random hwaddr
# Note on some boards, usb0 is automaticly setup with an init script
# in that case, to completely disable remove file [run_boot-scripts] from the boot partition
iface usb0 inet static
    address 192.168.7.2
    netmask 255.255.255.0
    network 192.168.7.0
    gateway 192.168.7.1
```

# At the end of ~/.bashrc add:

startxfce4

# In xfce add Radio.py to the startup programs

#Reboot
 
>** on one install this worked without errors, on another it told me that the jack server was not running, but worked with the usb sound card anyway.  I ignored the errors because every thing was working.**
