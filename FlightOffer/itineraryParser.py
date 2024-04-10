import re
from datetime import datetime, timedelta

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
        (?P<airline_code>[A-Z]{2})  # Airline IATA code - 2 letters
        \s*(?P<flight_number>\d+)  # Flight number - digits
        \s+[A-Z]\s+  # Skip the placeholder character and spaces
        (?P<date>\d{1,2}[A-Z]{3})  # Date - day and 3-letter month
        \s+\d\s+  # Skip day of the week and spaces
        (?P<source>[A-Z]{3})  # Source airport code - 3 letters
        (?P<destination>[A-Z]{3})  # Destination airport code - 3 letters
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
            flights.append({"departure": {"iataCode": flight["source"], "at": format_departure_time(flight['date'], flight["departure_time"], 0)}, "arrival": {"iataCode": flight["destination"], "at": format_departure_time(flight['date'], flight["arrival_time"], days_offset)}, "flightNumber": flight["flight_number"], "carrierCode": flight["airline_code"], "duration": duration, "iteraryNumber": None, "travelClass": None})
    return {"offers": [{"passengers": None, "fares": [], "flights": flights, "geoCode": {}, "airportName": None, "cityCode": None, "upsellOffers": []}]}

if __name__ == "__main__":
    text = """
    3  DL9267 X 14APR 7 VCEAMS HK2          1140 1340   *1A/E*
    4  DL 165 X 14APR 7 AMSMSP HK2          1520 1735   *1A/E*
    5  DL1411 X 14APR 7 MSPYWG HK2       1  2157 2325   *1A/E*
    6  AF8715 K 20APR 6 YWGMSP HK2  1150    1230 1402   *1A/E*
    7  AF3574 K 20APR 6 MSPCDG HK2  1550 1  1630 0755+1 *1A/E*
    8  AF1426 K 21APR 7 CDGVCE HK2  0900 2F 0940 1120   *1A/E*
    """

    parsed_data = parse_offer_text(text)
    print(parsed_data)