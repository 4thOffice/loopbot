# Function to check time difference between flights
import datetime
import re

def is_valid_time_format(time_string):
    pattern = r'^\d{2}:\d{2}:\d{2}$'  # HH:MM:SS format pattern
    return re.match(pattern, time_string) is not None

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
    found = False
    for itinerary in itineraries:
        segments = itinerary.get('segments', [])
        if numberOfStops == 2:
            if len(segments) >= (numberOfStops+1):
                found = True
        elif len(segments) > (numberOfStops+1):
            return True
        elif len(segments) == (numberOfStops+1):
            found = True
         
    if not found:
        return True

    return False

def get_time_difference_data(flight_offers, extraTimeframes):
    if extraTimeframes == {}:
        return flight_offers
    
    closest_offers = []
    for offer in flight_offers:
        if "offer" in offer:
            offer_ = offer["offer"]
        else:
            offer_ = offer
        time_diff = 0
        for index1, itinerary in enumerate(offer_['itineraries']):
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

def extract_numbers(s):
    numbers = re.findall(r'\d+', s)
    numbers_without_zeros = [str(int(num)) for num in numbers]
    return ''.join(numbers_without_zeros)


def getDuration(time_stamp1, time_stamp2):
    dt1 = datetime.fromisoformat(time_stamp1)
    dt2 = datetime.fromisoformat(time_stamp2)

    time_difference = dt2 - dt1

    total_hours = time_difference.total_seconds() / 3600

    duration = f"PT{int(total_hours):02d}H{time_difference.seconds//3600:02d}M"
    duration = duration.replace("0", "")

    return duration