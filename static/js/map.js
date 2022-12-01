// Initialize and add the map
function initMap() {
    // Extract center and coordinates from server
    var mean_coord = JSON.parse(document.getElementById("map").dataset.center)
    var coord = JSON.parse(document.getElementById("map").dataset.geocode)

    // The map, centered at average of all coordinates
    const center = { lat: mean_coord[0], lng: mean_coord[1] };
    const map = new google.maps.Map(document.getElementById("map"), {
        zoom: 6,
        center: center,
    });

    // Populate markers for route
    for (let i = 0; i < coord.length; i++) {
        const marker = new google.maps.Marker({
            position: new google.maps.LatLng(coord[i][0], coord[i][1]),
            map: map,
            label: {
                color: '#000',
                fontSize: '12px',
                fontWeight: '600',
                text: (i + 1).toString()
            }
        });
    }
}

window.initMap = initMap;