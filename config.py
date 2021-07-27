# ================================= #
#          Meraki Settings          #
# ================================= #

base_url = "https://api.meraki.com/api/v1"
meraki_api_key = " "
network_id = " "

# serial numbers of your sensors
# example ["xxxx-xxxx-xxx","xxxx-xxxx-xxx","xxxx-xxxx-xxx"] or leave empty []
temperature_sensors = ["  ", " "]


# ================================= #
#          INFLUX DB                #
# ================================= #

org = "merakiOrganization"
bucket = "merakiBucket"
token = " "
influx_url = "http://localhost:8086"


# ================================= #
#      ASHRAE SETTINGS              #
# ================================= #

ASHRAE_low = 10
ASHRAE_high = 30

# ================================= #
#       SENSOR MAPPINGS             #
# ================================= #

sensor_mapping = [
    {
        "name": " ",
        "serial": " ",
        "type": "temperature"
    },
    {
        "name": " ",
        "serial": " ",
        "type": "temperature"
    }
]
