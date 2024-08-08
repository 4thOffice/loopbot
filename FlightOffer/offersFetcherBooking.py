import requests
import json
from Auxiliary.verbose_checkpoint import verbose

def parse_search_params_to_new_format(search_params):
    # Map the originDestinations
    search_params = search_params['search_params']
    origin_destinations = []
    for od in search_params['originDestinations']:
        origin_destinations.append({
            "departure": {
                "airportCode": od['originLocationCode'],
                "date": od['departureDateTimeRange']['date']
            },
            "arrival": {
                "airportCode": od['destinationLocationCode']
            }
        })

    # Extract traveler counts
    travelers = {'ADT': 0, 'CHD': 0, 'INF': 0}
    for traveler in search_params['travelers']:
        if traveler['travelerType'] == 'ADULT':
            travelers['ADT'] += 1
        elif traveler['travelerType'] == 'CHILD':
            travelers['CHD'] += 1
        elif traveler['travelerType'] == 'INFANT':
            travelers['INF'] += 1

    # Determine cabin preference
    cabin_restriction = search_params['searchCriteria']['flightFilters']['cabinRestrictions'][0]
    cabin_map = {
        'ECONOMY': '5',
        'PREMIUM_ECONOMY': '4',
        'BUSINESS': '3',
        'FIRST': '2'
    }
    cabin_preference = [cabin_map[cabin_restriction['cabin']]]

    # Construct the new JSON format
    new_format = {
        "metadata": {
            "country": "SI",  # Assuming default country is Germany
            "currency": search_params['currencyCode'],
            "locale": "sl_SI"  # Assuming default locale is German
        },
        "originDestinations": origin_destinations,
        "preferences": {
            "cabin": cabin_preference,
            "nonStop": search_params['searchCriteria']['flightFilters']['connectionRestriction']['maximumNumberOfConnections'] == 0
        },
        "travelers": travelers
    }

    return new_format

def flightShoping(structuredData, verbose_checkpoint):
    
    
    base_url = 'https://proxy.airgateway.com/v1.2/AirShopping'
    headers = {
        'AG-Search-Mode':'cheapest_flights',
        'Content-Type': 'application/json',
        'Ag-Providers': '*',  
        'Authorization': '43dd04d25d7f565674baf30ca6dcfda8',  
    }
    
    data = parse_search_params_to_new_format(structuredData)

    response = requests.post(base_url, headers=headers, data=json.dumps(data))        
    if response.status_code == 200:  
        
        return {"status": "ok", "details": response.json()}
    else:
        
        return {"status code": response.status_code, "details": response.json()}
    