from gpiozero import MCP3008
import datetime as dt
from pip._vendor import requests
from threading import Timer
import logging

adcTrip1 = MCP3008(channel=0, max_voltage=3.3)
adcTrip2 = MCP3008(channel=1, max_voltage=3.3)
adcTemp = MCP3008(channel=2, max_voltage=3.3)

adcOrder = [0, 0]
globalPeopleInside = 0
checkSent = False
globalDidRun = False

SUBMIT_URL = "https://studev.groept.be/api/a22ib2b06/insertNewValues/"


class RepeatedTimer(object):  # timer object
    def __init__(self, interval, function, *args, **kwargs):  # initialize itself
        self._timer = None
        self.interval = interval
        self.function = function
        self.args = args
        self.kwargs = kwargs
        self.is_running = False
        self.start()

    def _run(self):  # run the inputted function
        self.is_running = False
        self.start()
        self.function(*self.args, **self.kwargs)

    def start(self):  # start itself and the timer
        if not self.is_running:
            self._timer = Timer(self.interval, self._run)
            self._timer.start()
            self.is_running = True

    def stop(self):  # stop itself and the timer
        self._timer.cancel()
        self.is_running = False


def checkIfPass(absVal):
    val = False
    if absVal <= 0.5:
        val = True
    return val


def countPeople(inside):  # count the amount of people inside based on the direction
    direction = directionDet(adcOrder)
    if direction == "in":
        newInside = inside + 1
        whenIrTriggered(newInside)
        return newInside
    elif direction == "out" and inside > 0:
        newInside = inside - 1
        whenIrTriggered(newInside)
        return newInside
    return inside


def getAmountOfPeopleInside():
    return globalPeopleInside


def directionDet(Order):  # determine the order of passage, in = incoming, out = outgoing
    checkTrips()

    if Order[0] == 1 and Order[1] == 2:
        logging.info("passed from 1 --> 2")
        resetAdcOrder()
        return "in"
    elif Order[0] == 2 and Order[1] == 1:
        logging.info("passed from 2 --> 1")
        resetAdcOrder()
        return "out"
    return


def whenIrTriggered(amountOfPeople):
    sentDbNewVal("IR", amountOfPeople, "people")
    resetAdcOrder()
    return


def checkTrips():  # checks which ir sensors are passed in wat order
    if checkIfPass(adcTrip1.value):
        if adcOrder[0] == 0:
            adcOrder[0] = 1
        elif adcOrder[0] == 2:
            adcOrder[1] = 1
    if checkIfPass(adcTrip2.value):
        if adcOrder[0] == 0:
            adcOrder[0] = 2
        elif adcOrder[0] == 1:
            adcOrder[1] = 2
    return


def resetAdcOrder():  # resets the Order of passed to 0
    while checkAnyTripActive():
        adcOrder[0] = 0
        adcOrder[1] = 0
    return


def checkAnyTripActive():  # checks if any of the IR sensors is blocked
    if checkIfPass(adcTrip1.value):
        return True
    if checkIfPass(adcTrip2.value):
        return True
    return False


def getTime(form):  # get time according to a certain format
    time = dt.datetime.now().strftime(form)
    return time


def getTemp():  # get the temperature
    temp = convertToTemp(adcTemp.value)
    temp = round(temp, 1)
    return temp


def sentDbNewVal(idSensor, value, unit):  # sent temperature data to data base via JSON
    idSensor = idSensor
    unit = unit
    if idSensor == "ntc":
        val = getTemp()
    else:
        val = value

    uploadStrN = SUBMIT_URL
    uploadStrN += idSensor
    uploadStrN += "/"
    uploadStrN += str(val)
    uploadStrN += "/"
    uploadStrN += unit

    resp = requests.get(uploadStrN)
    logging.info("statusCode: " + str(resp.status_code) + resp.text)
    logging.info("temp: " + str(val) + "adcTemp: " + str(adcTemp.value))
    return None


def convertToTemp(adcVal):  # function to convert NTC value to temp in °C
    v_dd = 3.326                            # voltage in Volts
    v_reff = v_dd
    r7 = 1674                               # resistance in ohm

    v_r7 = (adcVal / 1024 * v_reff) * 1000  # convert adc val to input voltage
    v_r7 = v_r7 * 0.715                     # taking into account gain of 1.4
    v_ntc = v_dd - v_r7

    r_ntc = r7 / ((v_dd / v_ntc) - 1)       # voltage divider transformed

    # linear relation resistor NTC and Temp
    b = 60.1818
    a = -0.0181818
    temp = a * r_ntc + b
    logging.info("temperature: " + str(temp))
    return temp


def run_once(didRun):  # a func to initialize the repeated timer for the temp
    if not didRun:
        RepeatedTimer(3.0, sentDbNewVal, "ntc", getTemp(), "C")
        didRun = True
    return didRun


while True:
    globalDidRun = run_once(globalDidRun)
    globalPeopleInside = countPeople(globalPeopleInside)
    logging.info("orderOfPassing: " + str(adcOrder) + "amountOfPeople: " + str(globalPeopleInside))
    # logging.getLogger().setLevel(logging.INFO)
