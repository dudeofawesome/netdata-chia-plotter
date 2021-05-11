## Installation (python)

1. ~~install chia-blockchain to `/usr/local/src/chia-blockchain`~~
1. ~~symlink `/var/lib/empty/.config/plotman/plotman.yaml` to your your `plotman.yaml` & make sure it's readable by user `netdata` (probably have to `chmod 750 ~/.config`)~~
1. ~~run netdata as root I guess? this is a bad idea~~
1. ~~`sudo cp /home/dudeofawesome/Github/netdata-chia-plotter/chia_plotter*.py /usr/libexec/netdata/python.d/; and sudo systemctl restart netdata.service`~~
1. `plotman status > /var/tmp/plotman-status.out` every 15 seconds
