function initMap() {
    var mean_coord = JSON.parse(document.getElementById("map").dataset.center)
    var coord = JSON.parse(document.getElementById("map").dataset.geocode)

    const map = new google.maps.Map(document.getElementById("map"), {
        zoom: 4,
        center: { lat: mean_coord[0], lng: mean_coord[1] }
    });
    const directionsService = new google.maps.DirectionsService();
    const directionsRenderer = new google.maps.DirectionsRenderer({
        map,
        panel: document.getElementById("panel"),
    });

    directionsRenderer.addListener("directions_changed", () => {
        const directions = directionsRenderer.getDirections();

        if (directions) {
            computeTotalDistance(directions);
        }
    });
    displayRoute(
        coord,
        directionsService,
        directionsRenderer
    );
}

function displayRoute(coord, service, display) {
    var waypoints = []

    for (let i = 0; i < coord.length; i++) {
        waypoints.push({ location: coord[i] })
    }

    const list_length = waypoints.length

    service
        .route({
            origin: waypoints[0],
            destination: waypoints[list_length - 1],
            waypoints: waypoints.slice(1, list_length - 1),
            travelMode: google.maps.TravelMode.DRIVING,
            avoidTolls: true,
        })
        .then((result) => {
            display.setDirections(result);
        })
        .catch((e) => {
            alert("Could not display directions due to: " + e);
        });
}

function computeTotalDistance(result) {
    let total = 0;
    const myroute = result.routes[0];

    if (!myroute) {
        return;
    }

    for (let i = 0; i < myroute.legs.length; i++) {
        total += myroute.legs[i].distance.value;
    }

    total = total / 1000;
    document.getElementById("total").innerHTML = total + " km";
}

window.initMap = initMap;