import re
from datetime import datetime, timedelta
import math

def check_if_anything_after(text, specific_line_number):
    for line_number, line in enumerate(text.split('\n')):
        if line_number > specific_line_number:
            if line.strip():  # Check if the line has any non-whitespace characters
                return True  # There is text after the specific line
    return False  # No text found after the specific line


def split_itineraries(text):
    itineraries = []
    current_itinerary = []

    last_number = math.inf
    for line_number, line in enumerate(text.split('\n')):
        if line.strip():  # Check if the line is not empty
            match = re.match(r'(\d+)', line)  # Find the full first number
            if match:
                first_number = int(match.group(1))  # Extract the first number
                print("first number:", first_number)
                print("last number:", last_number)
                if first_number <= last_number:  # If it's the start of a new itinerary
                    itineraries.append('\n'.join(current_itinerary))
                    print("added")
                    print('\n'.join(current_itinerary))
                    current_itinerary = [line]
                    last_number = first_number
                elif not check_if_anything_after(text, line_number):
                    current_itinerary.append(line)
                    itineraries.append('\n'.join(current_itinerary))
                    print("added")
                    print('\n'.join(current_itinerary))
                    current_itinerary = [line]
                    last_number = first_number
                else:
                    current_itinerary.append(line)
            else:
                if current_itinerary:  # If there is an itinerary being built, add the line to it
                    current_itinerary.append(line)

    # Add the last itinerary
    if current_itinerary:
        itineraries.append('\n'.join(current_itinerary))

    return itineraries

# Function to parse the given string time format "HHMM+X" where "+X" is optional
def time_from_string(time_str):
    day_offset = 0
    if '+' in time_str:
        time_str, offset_str = time_str.split('+')
        day_offset = int(offset_str)

    time_str = time_str.zfill(4)
    base_time = datetime.strptime(time_str, '%H%M')
    final_time = base_time + timedelta(days=day_offset)
    
    return final_time

# Function to calculate the time difference between two times
def calculate_time_difference(start, end):
    start_time = time_from_string(start)
    end_time = time_from_string(end)
    seconds1 = (start_time.hour * 3600) + (start_time.minute * 60) + start_time.second
    seconds2 = (end_time.hour * 3600) + (end_time.minute * 60) + end_time.second
    difference_in_seconds = seconds2 - seconds1
    if difference_in_seconds < 0:
        difference_in_seconds += 86400
    hours, rem = divmod(difference_in_seconds, 3600)
    minutes, seconds = divmod(rem, 60)

    return 'PT{:02}H{:02}M'.format(int(hours), int(minutes))

def format_departure_time(date_string, time_string, days_offset):
    date_str = date_string
    departure_time_str = time_string.split("+")[0]
    year_str = "2024"  # Assuming the year to use based on your requirement
    date_obj = datetime.strptime(f"{date_str}{year_str}", "%d%b%Y")
    time_obj = datetime.strptime(departure_time_str, "%H%M").time()
    combined_datetime = datetime.combine(date_obj.date(), time_obj)
    combined_datetime += timedelta(days=days_offset)

    formatted_datetime = combined_datetime.strftime("%Y-%m-%dT%H:%M:%S")

    return formatted_datetime

def parse_time(time_str):
    return datetime.strptime(time_str, '%H%M').time()

def parse_date(date_str):
    today = datetime.now().date()
    return (today if date_str == '1' else today + timedelta(days=int(date_str)))

def parse_flight_info(text):
    # Define regular expression patterns to extract information
    pattern = r"""
        (?P<airline_code>[A-Za-z]{2})  # Airline IATA code - 2 letters
        \s*(?P<flight_number>\d+)  # Flight number - digits
        (?:\s+)?  # Skip optional spaces
        (?:[A-Za-z]\s+)?  # Skip the placeholder character 'X' and spaces if present
        (?P<date>\d{1,2}[A-Z]{3})  # Date - day and 3-letter month
        (?:\s+\d\s+)?(.+)  # Skip day of the week and spaces
        (?P<source>[A-Za-z]{3})  # Source airport code - 3 letters
        (?P<destination>[A-Za-z]{3})  # Destination airport code - 3 letters
        .*?  # Skip placeholder and spaces
        (?P<departure_time>\d{4}(?:\+\d+)?)   # Departure time - 4 digits
        \s+
        (?P<arrival_time>\d{4}(?:\+\d+)?)  # Arrival time - 4 digits
    """
    
    match = re.search(pattern, text, re.VERBOSE)

    if match:
        details = match.groupdict()
        return details
    else:
        return None

def parse_offer_text(text):
    flights = []
    for line in text.split('\n'):
        print(f".{line}.")
        flight = parse_flight_info(line)
        print(flight)
        if flight:
            offset_split = flight["arrival_time"].split("+")
            days_offset = 0
            if len(offset_split) >= 2:
                days_offset = int(offset_split[1])

            duration = calculate_time_difference(flight["departure_time"], flight["arrival_time"])
            flights.append({"departure": {"iataCode": flight["source"].upper(), "at": format_departure_time(flight['date'].upper(), flight["departure_time"], 0)}, "arrival": {"iataCode": flight["destination"].upper(), "at": format_departure_time(flight['date'].upper(), flight["arrival_time"], days_offset)}, "flightNumber": flight["flight_number"], "carrierCode": flight["airline_code"].upper(), "duration": duration, "iteraryNumber": None, "travelClass": None})
    return {"passengers": None, "fares": [], "flights": flights, "geoCode": {}, "airportName": None, "cityCode": None, "upsellOffers": []}


def get_offer_data(text):
    offers = {"offers": []}
    #itineraries = split_itineraries(text)
    itineraries = re.split(r'split|---', text)
    for itinerary in itineraries:
        print("=========")
        print(itinerary)
        offer = parse_offer_text(itinerary)
        if offer["flights"]:
            offers["offers"].append(offer)

    return offers

if __name__ == "__main__":
    text = """
1.OZBOT/ZAN MR
2  LO 618 L 07MAY 2 LJUWAW HK1          1705 1835   *1A/E* 1 
3  LO 617 S 11MAY 6 WAWLJU HK1          1445 1625   *1A/E*

split 1.OZBOT/ZAN MR
2  LO 618 L 07MAY 2 LJUWAW HK1          1705 1835   *1A/E* 2
3  LO 617 S 11MAY 6 WAWLJU HK1          1445 1625   *1A/E*

---

1.OZBOT/ZAN MR
2  LO 618 L 07MAY 2 LJUWAW HK1          1705 1835   *1A/E* 3
3  LO 617 S 11MAY 6 WAWZAR HK1          1445 1625   *1A/E*
    """

    parsed_data = get_offer_data(text)
    print(parsed_data)