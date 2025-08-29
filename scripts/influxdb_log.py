"""Script for logging to InfluxDB."""
import time
import sys
import json
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
import ptc10

# cfg_file = files('scripts'), 'influxdb_config.json')

def main(config_file):
    """Query user for setup info and start logging to InfluxDB."""

    ## read config file
    with open(config_file, encoding='utf-8') as cfg_file:
        cfg = json.load(cfg_file)

    verbose = cfg['verbose'] == 1

    ## Connect to InfluxDB
    if verbose:
        print("Connecting to InfluxDB...")
    db_client = InfluxDBClient(url=cfg['url'], token=cfg['db_token'], org=cfg['org'])
    write_api = db_client.write_api(write_options=SYNCHRONOUS)

    ## Connect to GammaVac PTC10
    if verbose:
        print("Connecting to SRS PTC10 controller...")
    ptc = ptc10.PTC10.connect(method="ethernet", host="192.168.29.150", tcp_port=23)

    ## Check pump status
    if 'Running' in gv.get_pump_status():
        gv.set_units("T")   # set units to Torr
        try:
            while True:
                ## Pressure
                pressure = gv.read_pressure()
                ppoint = (
                    Point("srs_ptc10")
                    .field("pressure", pressure)
                    .tag("units", "Torr")
                    .tag("channel", f"{cfg['channel']}")
                )
                write_api.write(bucket=cfg['bucket'], org=cfg['org'], record=ppoint)
                if verbose:
                    print(ppoint)
                current = gv.read_current()
                ## Current
                cpoint = (
                    Point("srs_ptc10")
                    .field("current", current)
                    .tag("units", "Amps")
                    .tag("channel", f"{cfg['channel']}")
                )
                write_api.write(bucket=cfg['bucket'], org=cfg['org'], record=cpoint)
                if verbose:
                    print(cpoint)
                ## Voltage
                voltage = gv.read_voltage()
                vpoint = (
                    Point("srs_ptc10")
                    .field("voltage", voltage)
                    .tag("units", "Volts")
                    .tag("channel", f"{cfg['channel']}")
                )
                write_api.write(bucket=cfg['bucket'], org=cfg['org'], record=vpoint)
                if verbose:
                    print(vpoint)
                # Sleep for interval_secs
                time.sleep(cfg['interval_secs'])

        except KeyboardInterrupt:
            print("\nShutting down InfluxDB logging...")
            db_client.close()
            gv.disconnect()
    else:
        print("Pump not running")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python influxdb_log.py <influxdb_log.json>")
        sys.exit(0)
    main(sys.argv[1])
