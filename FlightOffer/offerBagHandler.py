from Auxiliary.verbose_checkpoint import verbose

def addBags(offers, checkedBags, get_price_offer, access_token, verbose_checkpoint):
    for index, offer in enumerate(offers):
        bagsAdded = False
        oldPrice = offer["price"]["grandTotal"]
        for traveler in offer["travelerPricings"]:
            for segment in traveler["fareDetailsBySegment"]:
                if "quantity" in segment["includedCheckedBags"]:
                    includedBagsInSegment = segment["includedCheckedBags"]["quantity"]
                else:
                    includedBagsInSegment = 1
                bagsToAdd = checkedBags - includedBagsInSegment
                if bagsToAdd > 0:
                    bagsAdded = True
                    segment["additionalServices"] = {"chargeableCheckedBags": {"quantity": bagsToAdd}}
        
        if bagsAdded:
            try:
                priceOfferWithbags = get_price_offer(access_token, [offer])["data"]["flightOffers"][0]
            except Exception:
                verbose(f"Offer {index}: error fetching price for offer with additional checked bags", verbose_checkpoint)
                print(f"Offer {index}: error fetching price for offer with additional checked bags")
                continue
            offers[index] = priceOfferWithbags
            offer = offers[index]
            newPrice = offer["price"]["grandTotal"]
            verbose(f"Offer {index}: price without additional checked bags: {oldPrice}\nPrice with additional checked bags: {newPrice}\n", verbose_checkpoint)
            print(f"Offer {index}: price without additional checked bags: {oldPrice}\nPrice with additional checked bags: {newPrice}\n")

    return offers