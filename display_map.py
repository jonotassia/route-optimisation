# Directs the flask server to display Folium map output.
import geolocation
from flask import Flask


app = Flask(__name__)


@app.route('/')
def index(coord_list, visit_list):
    return geolocation.display_route_in_browser(coord_list, visit_list)


if __name__ == "__main__":
    app.run()

