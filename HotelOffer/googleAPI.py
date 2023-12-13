import requests
import json
import sys
import requests
import os
if os.path.dirname(os.path.realpath(__file__)) not in sys.path:
    sys.path.append(os.path.dirname(os.path.realpath(__file__)))

sys.path.append("../")
import keys

def get_place_id(latitude, longitude, radius, query, google_key=keys.google_places_APIKEY):
    query = query
    lat_lng = f'{latitude},{longitude}'
    base_url = 'https://maps.googleapis.com/maps/api/place/textsearch/json'
    params = '?location=' + lat_lng + '&query=' + query + '&radius=' + str(radius) + '&key=' + google_key
    url = base_url + params

    headers = { 'Accept': 'application/json' }
    
    response = requests.request('GET', url, headers=headers, data={})
    json_response = json.loads(response.text)
    place_id = json_response['results'][0]['place_id']
    return place_id

# Place Details API
def place_details(place_id, google_key=keys.google_places_APIKEY): 
    url = 'https://maps.googleapis.com/maps/api/place/details/json?place_id=' + place_id + '&key=' + google_key

    headers = { 'Accept': 'application/json' }

    response = requests.request('GET', url, headers=headers, data={})
    json_response = json.loads(response.text)

    photo_references = []
    for i in range(len(json_response['result']['photos'])):
        photo_references.append(json_response['result']['photos'][i]['photo_reference']
    )
    return photo_references

# Place Photos API 
def place_photos(photo_reference, google_key=keys.google_places_APIKEY): 
    url = 'https://maps.googleapis.com/maps/api/place/photo?maxwidth=400&photoreference=' + photo_reference + '&key=' + google_key

    headers = {
    'Accept': 'image/*'
    }

    response = requests.request('GET', url, headers=headers, data={})
    if response.status_code == 200:
        return response
    else:
        print(f'Failed to retrieve google photos data: {response.status_code} - {response.text}')
        return None
#https://www.google.com/maps/search/?api=1&query=Google&query_place_id=ChIJv83Z0UHPD4gRYoUZRpiWPQ0
#place_id = get_place_id()
#print(place_id)