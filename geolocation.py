# Contains functions related to geolocation using Placekey API
import boto3
from placekey.api import PlacekeyAPI

# Initiate AWS SSM integration for secrets storage
ssm = boto3.client('ssm')

# Grab api key from AWS
placekey_api_key = ssm.get_parameter(Name="placekey_api_key")
pk_api = PlacekeyAPI(placekey_api_key)
