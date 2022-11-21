# Contains functions related to geolocation using Placekey API
import boto3
from placekey.api import PlacekeyAPI

# Initiate AWS SSM integration for secrets storage
ssm = boto3.client('ssm')

# Grab api key from AWS
placekey_api_key = ssm.get_parameter(Name="placekey_api_key")
pk_api = PlacekeyAPI(placekey_api_key)

# query.street_address:14907 SE Newport Way
# query.city:Bellevue
# query.region:WA
# query.postal_code:98006
# query.iso_country_code:US
