import datetime


"""if item['latestDepartureTime'] and item['earliestArrivalTime']:
    old_latest_departure_time = datetime.datetime.strptime(item['latestDepartureTime'], "%H:%M:%S")
    old_earliest_arrival_time = datetime.datetime.strptime(item['earliestArrivalTime'], "%H:%M:%S")
    new_latest_departure_time = old_latest_departure_time + datetime.timedelta(hours=0.5)
    new_earliest_arrival_time = old_earliest_arrival_time - datetime.timedelta(hours=0.5)
    if new_latest_departure_time >= new_earliest_arrival_time:
        indexesToSkip.append(timeframeIndex)
        break

if item['earliestDepartureTime'] and item['latestArrivalTime']:
    old_earliest_departure_time = datetime.datetime.strptime(item['earliestDepartureTime'], "%H:%M:%S")
    old_latest_arrival_time = datetime.datetime.strptime(item['latestArrivalTime'], "%H:%M:%S")
    new_earliest_departure_time = old_earliest_departure_time - datetime.timedelta(hours=0.5)
    new_latest_arrival_time = old_latest_arrival_time + datetime.timedelta(hours=0.5)
    if new_earliest_departure_time >= new_latest_arrival_time:
        indexesToSkip.append(timeframeIndex)
        break"""

def expandTimeframes(timeframes):
    end = True
    for timeframeIndex, item in enumerate(timeframes):
        if not (item['latestDepartureTime'] or item['earliestArrivalTime'] or item['earliestDepartureTime'] or item['latestArrivalTime']):
            continue

        if item['latestDepartureTime']:
            latest_departure_time = datetime.datetime.strptime(item['latestDepartureTime'], "%H:%M:%S")
            new_latest_departure_time = latest_departure_time + datetime.timedelta(hours=0.5)
            if not new_latest_departure_time >= datetime.datetime.strptime("23:59:59", "%H:%M:%S"):
                item['latestDepartureTime'] = new_latest_departure_time.strftime("%H:%M:%S")
                end = False

        if item['earliestArrivalTime']:
            earliest_arrival_time = datetime.datetime.strptime(item['earliestArrivalTime'], "%H:%M:%S")
            new_earliest_arrival_time = earliest_arrival_time - datetime.timedelta(hours=0.5)
            if not new_earliest_arrival_time <= datetime.datetime.strptime("00:00:00", "%H:%M:%S"):
                item['earliestArrivalTime'] = new_earliest_arrival_time.strftime("%H:%M:%S")
                end = False

        if item['latestArrivalTime']:
            latest_arrival_time = datetime.datetime.strptime(item['latestArrivalTime'], "%H:%M:%S")
            new_latest_arrival_time = latest_arrival_time + datetime.timedelta(hours=0.5)
            if not new_latest_arrival_time >= datetime.datetime.strptime("23:59:59", "%H:%M:%S"):
                item['latestArrivalTime'] = new_latest_arrival_time.strftime("%H:%M:%S")
                end = False

        if item['earliestDepartureTime']:
            earliest_departure_time = datetime.datetime.strptime(item['earliestDepartureTime'], "%H:%M:%S")
            new_earliest_departure_time = earliest_departure_time - datetime.timedelta(hours=0.5)
            if not new_earliest_departure_time <= datetime.datetime.strptime("00:00:00", "%H:%M:%S"):
                item['earliestDepartureTime'] = new_earliest_departure_time.strftime("%H:%M:%S")
                end = False

    return timeframes, end


#extraTimeframes = [{'earliestDepartureTime': '', 'latestDepartureTime': '', 'exactDepartureTime': '', 'earliestArrivalTime': '', 'latestArrivalTime': '', 'exactArrivalTime': ''}, {'earliestDepartureTime': '', 'latestDepartureTime': '', 'exactDepartureTime': '', 'earliestArrivalTime': '', 'latestArrivalTime': '', 'exactArrivalTime': ''}]
#timeframes, end = expandTimeframes(extraTimeframes)
#print(timeframes)
#print(end)