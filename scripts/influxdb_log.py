"""Script for logging to InfluxDB."""
import time
import sys
import json
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
from urllib3.exceptions import ReadTimeoutError
import ptc10

# cfg_file = files('scripts'), 'influxdb_config.json')


def main(config_file):
    """Query user for setup info and start logging to InfluxDB."""

    # read the config file
    with open(config_file, encoding='utf-8') as cfg_file:
        cfg = json.load(cfg_file)

    verbose = cfg['verbose'] == 1

    # Connect to SRS PTC10
    if verbose:
        print("Connecting to SRS PTC10 controller...")
    ptc = ptc10.PTC10()
    ptc.connect(host=cfg['device_host'], port=cfg['device_port'])

    # Try/except to catch exceptions
    db_client = None
    try:
        # Loop until ctrl-C
        while True:
            try:
                # Connect to InfluxDB
                if verbose:
                    print("Connecting to InfluxDB...")
                db_client = InfluxDBClient(url=cfg['db_url'], token=cfg['db_token'],
                                           org=cfg['db_org'])
                write_api = db_client.write_api(write_options=SYNCHRONOUS)
                channels = cfg['log_channels']

                for chan in channels:
                    value = ptc.get_channel_value(chan)
                    point = (
                        Point("srs_ptc10")
                        .field(channels[chan]['field'], value)
                        .tag("units", channels[chan]['units'])
                        .tag("channel", f"{cfg['db_channel']}")
                    )
                    write_api.write(bucket=cfg['db_bucket'], org=cfg['db_org'], record=point)
                    if verbose:
                        print(point)

                # Close db connection
                if verbose:
                    print("Closing connection to InfluxDB...")
                db_client.close()
                db_client = None
            # Handle exceptions
            except ReadTimeoutError as e:
                if verbose:
                    print(f"ReadTimeoutError occurred: {e}, will retry.")
            except Exception as e:
                print(f"Unexpected error: {e}, will retry.")

            # Sleep for interval_secs
            if verbose:
                print(f"Waiting {cfg['interval_secs']:d} seconds...")
            time.sleep(cfg['interval_secs'])

    except KeyboardInterrupt:
        print("\nShutting down InfluxDB logging...")
        if db_client:
            db_client.close()
        ptc.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python influxdb_log.py <influxdb_log.json>")
        sys.exit(0)
    main(sys.argv[1])
