from datetime import datetime, timedelta
import json
import re
import openai
import sys
sys.path.append("../")
import keys

def iso_to_custom_date(iso_date):
    parsed_date = datetime.fromisoformat(iso_date)
    return parsed_date.strftime("%d%b").upper()

# Function to calculate duration in hours and minutes from ISO duration string
def iso_to_hours_minutes(iso_duration):
    duration = re.match(r'PT(\d+)H(?:(\d+)M)?', iso_duration)
    if duration:
        hours = int(duration.group(1))
        minutes = int(duration.group(2)) if duration.group(2) else 0
        return f"{hours:02d}h:{minutes:02d}min"
    else:
        return "00h:00min"
    
def generateOffer(emailText, details):
    print("---------------------")
    print(details)
    # Generating the output strings
    flights_string = generateFlightsString(details)

    user_msg = "I will give you a flight tender enquiry email. I want you to generate an offer i can send back. Do NOT make up data. Email should be as short as possible(maximum 80 words) and formal. Do not include subject.\n\nThe following text in curly brackets is flight details and should be in thsi exact format in the final email you write:\n"
    user_msg += "{" + flights_string + "}"

    user_msg += "\n\nEmail I want you to respond to:\n"
    user_msg += emailText
    user_msg += "\n\nRespond in same language as the email you are replying to."
    user_msg += "\n\nYour reply should ONLY be email text and NO other text."
    
    print(user_msg)

    openai.api_key = keys.openAI_APIKEY
    response = openai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "user", "content": user_msg}
        ]
    )

    if response.choices:
        print("Offer generated successfuly.")
        generatedOffer = response.choices[0].message.content
        return generatedOffer
    else:
        print("Unexpected or empty response received.")

def generateFlightsString(details):
    flights_string = ""
    for flight in details["flights"]:
        departure_date = iso_to_custom_date(flight["departure"]["at"])
        duration = iso_to_hours_minutes(flight["duration"])
        flight_number = flight["carrierCode"] + " " + flight["flightNumber"]
        origin = flight["departure"]["iataCode"]
        destination = flight["arrival"]["iataCode"]
        arrival_time = datetime.fromisoformat(flight["arrival"]["at"]).strftime("%H:%M")
        departure_time = datetime.fromisoformat(flight["departure"]["at"]).strftime("%H:%M")
        
        flights_string += f"{flight_number:<8} {departure_date}  {origin}{destination:<12} {departure_time}-{arrival_time} ({duration})\n"

    flights_string += "Price: " + details["price"]["grandTotal"] + " " + details["price"]["billingCurrency"]

    return flights_string