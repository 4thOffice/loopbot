import json
import requests

apiType = "Enterprise"
def create_order_API(flight_offers, travelers, contacts, ama_Client_Ref, access_token):
    if apiType == "personal":
        url = 'https://api.amadeus.com/v1/booking/flight-offers'
    else:
        url = 'https://travel.api.amadeus.com/v1/booking/flight-orders'
        
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/vnd.amadeus+json',
        'ama-Client-Ref': ama_Client_Ref
    }
    payload = {
        'data': {
            'type': 'flight-order',
            'flightOffers': flight_offers,
            'travelers': travelers,
            'contacts': contacts
        }
    }
    
    print(payload)

    response = requests.post(url, headers=headers, data=json.dumps(payload))
    if response.status_code == 201:
        print('Flight order created successfully!')
        print(response.json())
        return response.json()  # Return the JSON response
    else:
        print(f'Failed to retrieve data: {response.status_code} - {response.text}')
        return None
    
def create_order(flight_offers, people, ama_Client_Ref, access_token):
    offers_to_order = [flight_offers[0][0]["fare"]]

    print("offer to create order for:\n", offers_to_order)

    travelers = []
    for index, traveler in enumerate(people):
        travelers.append({
            "id": index+1,
            "name": {
                "firstName": traveler["first_name"],
                "lastName": traveler["last_name"]
            },
            "contact":{
                "phones":[
                    {
                        "deviceType": "LANDLINE",
                        "countryCallingCode": "386",
                        "number": "51385823"
                    }
                ],
                "emailAddress": "letalo@nomago.si"
            }
        })

    print("travelers\n", travelers)

    contacts = [
      {
        "addresseeName": {
          "firstName": "LOOP",
          "lastName": "NOMAGO"
        },
        "companyName": "NOMAGO",
        "purpose": "STANDARD",
        "phones": [
          {
            "deviceType": "LANDLINE",
            "countryCallingCode": "386",
            "number": "51385823"
          }
        ],
        "emailAddress": "letalo@nomago.si",
        "address": {
          "lines": [
            "Vošnjakova ulica, 3"
          ],
          "postalCode": "1000",
          "cityName": "Ljubljana",
          "countryCode": "SI"
        }
      }
    ]

    order_info = create_order_API(offers_to_order, travelers, contacts, ama_Client_Ref, access_token)
    order_reference = order_info["data"]["associatedRecords"][0]["reference"]

    return order_reference