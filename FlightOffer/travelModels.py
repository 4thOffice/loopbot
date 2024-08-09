from dataclasses import dataclass
from mongoengine import EmbeddedDocument, EmbeddedDocumentField, ListField, StringField, DictField, FloatField

@dataclass
class OfferResult:
    loop_chat_message: str
    offer_details: dict
    


class GeoCode(EmbeddedDocument):
    geoCode = StringField()

    def __str__(self):
        return f"GeoCode: {self.geoCode}"

class AirportName(EmbeddedDocument):
    airportName = StringField()
    
    def __str__(self):
        return f"AirportName: {self.airportName}"

class CityCode(EmbeddedDocument):
    cityCode = StringField()
    
    def __str__(self):
        return f"CityCode: {self.cityCode}"

class Passengers(EmbeddedDocument):
    passengers = StringField()

    def to_float(self):
        try:
            return float(self.passengers)
        except ValueError:
            print("Error: passengers value cannot be converted to float")
            return None
    
    def __str__(self):
        return f"Passengers: {self.passengers}"

class Price(EmbeddedDocument):
    grandTotal = FloatField()
    billingCurrency = StringField()
    
    def __str__(self):
        return f"{{'Grand total': {self.grandTotal}, 'Billing currency': '{self.billingCurrency}'}}"
    
class Fare(EmbeddedDocument):
    amenities = StringField()
    price = EmbeddedDocumentField(Price)
    checkedBags = StringField()
    
    def __str__(self):
        return f"Fare(Amenities: {self.amenities}, Price: {self.price}, CheckedBags: {self.checkedBags})"

class Flight(EmbeddedDocument):
    departure = StringField()
    arrival = StringField()
    duration = StringField()
    flightNumber = StringField()
    carrierCode = StringField()
    iteraryNumber = StringField()
    travelClass = StringField()
    
    def __str__(self):
        return (f"Flight(Departure: {self.departure}, Arrival: {self.arrival}, Duration: {self.duration}, "
                f"FlightNumber: {self.flightNumber}, CarrierCode: {self.carrierCode}, "
                f"IteraryNumber: {self.iteraryNumber}, TravelClass: {self.travelClass})")

class FlightOffer(EmbeddedDocument):
    api = StringField()
    passengers = EmbeddedDocumentField(Passengers)
    fares = ListField(EmbeddedDocumentField(Fare))
    flights = ListField(EmbeddedDocumentField(Flight))
    geoCode = EmbeddedDocumentField(GeoCode)
    airportName = EmbeddedDocumentField(AirportName)
    cityCode = EmbeddedDocumentField(CityCode)
    offer = DictField()    
    
    # upsellOffer = EmbeddedDocumentField(HotelOffers)  
    
    upsellOffer = None
    def get_passengers_as_float(self):
        if self.passengers:
            return self.passengers.to_float()
        return None
    
    def __str__(self):
        return (f"FlightOffer(Passengers: {self.passengers}, Fares: {self.fares}, Flights: {self.flights}, "
                f"GeoCode: {self.geoCode}, AirportName: {self.airportName}, CityCode: {self.cityCode}, "
                f"UpsellOffer: {self.upsellOffer}) API {self.api}")

