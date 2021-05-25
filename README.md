## Installation (python)

1. ~~install chia-blockchain to `/usr/local/src/chia-blockchain`~~
1. ~~symlink `/var/lib/empty/.config/plotman/plotman.yaml` to your your `plotman.yaml` & make sure it's readable by user `netdata` (probably have to `chmod 750 ~/.config`)~~
1. ~~run netdata as root I guess? this is a bad idea~~
1. ` sudo cp ~/Github/netdata-chia-plotter/chia_plotter*.py /usr/libexec/netdata/python.d/; sudo cp ~/Github/netdata-chia-plotter/*.conf /etc/netdata/python.d/; and sudo systemctl restart netdata.service`
1. install https://github.com/dudeofawesome/plotman
   `pip install --force-reinstall git+https://github.com/dudeofawesome/plotman@main`
1. `sudo systemctl enable ~/Github/netdata-chia-plotter/plotman-status-puller.timer`
1. `sudo systemctl enable ~/Github/netdata-chia-plotter/plotman-status-puller.service`
1. `sudo cp ~/Github/netdata-chia-plotter/dashboards/*.html /usr/share/netdata/web/`
1. `sudo chown root:netdata /usr/share/netdata/web/chia.html`
