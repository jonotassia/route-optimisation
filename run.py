# Generates Flask server for displaying the map
import flask
from flask import Flask
import boto3

ssm = boto3.client('ssm')

app = Flask(__name__)
google_api_key = ssm.get_parameter(Name="GOOGLE_CLOUD_API_KEY", WithDecryption=True)["Parameter"]["Value"]


@app.route("/")
def index():
    ordered_route = [
        (34.100376, -118.294640),
        (40.575245, -73.978577),
        (40.703693, -74.052315),
        (28.063587, -82.831558),
        (39.345097, -84.272026),
        (27.988932, -81.691345)
    ]
    return flask.render_template('map.html', geocode=ordered_route)


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080, debug=True)
