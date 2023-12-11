# Function to check time difference between flights
import datetime


def check_time_between_flights(itineraries, buffer):
    for itinerary in itineraries:
        segments = itinerary.get('segments', [])
        for i in range(len(segments) - 1):
            current_arrival_time = datetime.datetime.fromisoformat(segments[i]['arrival']['at'])
            next_departure_time = datetime.datetime.fromisoformat(segments[i + 1]['departure']['at'])
            time_difference = next_departure_time - current_arrival_time
            hours_difference = time_difference.total_seconds() / 3600

            if hours_difference > (2.5+buffer) or hours_difference < 1.7:
                return True

    return False

def check_number_of_stops(itineraries, numberOfStops):
    for itinerary in itineraries:
        segments = itinerary.get('segments', [])
        if numberOfStops == 2:
            if len(segments) < (numberOfStops+1):
                return True
        elif len(segments) != (numberOfStops+1):
            return True

    return False

def get_time_difference_data(flight_offers, extraTimeframes):
    if extraTimeframes == {}:
        return flight_offers
    
    closest_offers = []
    for offer in flight_offers:
        time_diff = 0
        for index1, itinerary in enumerate(offer['itineraries']):
            departure_time = itinerary['segments'][0]['departure']['at']
            arrival_time = itinerary['segments'][-1]['arrival']['at']

            departure_time = datetime.datetime.fromisoformat(departure_time).time()
            arrival_time = datetime.datetime.fromisoformat(arrival_time).time()

            if "exactDepartureTime" in extraTimeframes[index1] and extraTimeframes[index1]["exactDepartureTime"] != "":
                exactDepartureTime = datetime.datetime.strptime(extraTimeframes[index1]["exactDepartureTime"], '%H:%M:%S').time()
                time_diff += abs((departure_time.hour + departure_time.minute) - (exactDepartureTime.hour + exactDepartureTime.minute))
                print(abs((departure_time.hour + departure_time.minute) - (exactDepartureTime.hour + exactDepartureTime.minute)))
            if "exactArrivalTime" in extraTimeframes[index1] and extraTimeframes[index1]["exactArrivalTime"] != "":
                exactArrivalTime = datetime.datetime.strptime(extraTimeframes[index1]["exactArrivalTime"], '%H:%M:%S').time()
                time_diff += abs((arrival_time.hour + arrival_time.minute) - (exactArrivalTime.hour + exactArrivalTime.minute))
                print(abs((arrival_time.hour + arrival_time.minute) - (exactArrivalTime.hour + exactArrivalTime.minute)))
        closest_offers.append({"offer": offer, "time_difference": time_diff})

    return closest_offers