import amaduesFlightSearch
import bookingpadFlightSearch

def callFlightApis(structuredData, automatic_order, ama_Client_Ref, verbose_checkpoint):
     
    # detailsBookingpad = bookingpadFlightSearch.getFlightOffer(structuredData, verbose_checkpoint)
    # print(detailsBookingpad)
    detailsAmadeus = amaduesFlightSearch.getFlightOffer(structuredData, automatic_order, ama_Client_Ref, verbose_checkpoint)
    print(detailsAmadeus)
    # combined_offers = detailsBookingpad + detailsAmadeus
    
    # print(f'\n\nStevilo Amadeus ponudb: {(len(detailsAmadeus))}, Stevilo BookingPad ponudb: {(len(detailsBookingpad))}, skupaj {(len(combined_offers))}')