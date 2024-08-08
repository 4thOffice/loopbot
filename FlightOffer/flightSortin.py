import amaduesFlightSearch
import bookingpadFlightSearch

def callFlightApis(structuredData, automatic_order, ama_Client_Ref, verbose_checkpoint):
     
    # detailsBookingpad = bookingpadFlightSearch.getFlightOffer(structuredData, verbose_checkpoint)
    detailsAmadeus = amaduesFlightSearch.getFlightOffer(structuredData, automatic_order, ama_Client_Ref, verbose_checkpoint)