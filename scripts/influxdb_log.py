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

    ## Connect to SRS PTC10
    if verbose:
        print("Connecting to SRS PTC10 controller...")
    ptc = ptc10.PTC10()
    ptc.connect(host=cfg['device_host'], port=cfg['device_port'])

    try:
        while True:
            ## Temperature
            temperature = ptc.get_channel_value('A2')
            tpoint = (
                Point("srs_ptc10")
                .field("temperature", temperature)
                .tag("units", "degC")
                .tag("channel", f"{cfg['channel']}")
            )
            write_api.write(bucket=cfg['bucket'], org=cfg['org'], record=tpoint)
            if verbose:
                print(tpoint)
            ## Power
            output = ptc.get_channel_value('Out 1')
            ppoint = (
                Point("srs_ptc10")
                .field("output", output)
                .tag("units", "Amps")
                .tag("channel", f"{cfg['channel']}")
            )
            write_api.write(bucket=cfg['bucket'], org=cfg['org'], record=ppoint)
            if verbose:
                print(ppoint)

            # Sleep for interval_secs
            time.sleep(cfg['interval_secs'])

    except KeyboardInterrupt:
        print("\nShutting down InfluxDB logging...")
        db_client.close()
        ptc.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python influxdb_log.py <influxdb_log.json>")
        sys.exit(0)
    main(sys.argv[1])
