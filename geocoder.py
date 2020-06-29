import os

import geopy


API_KEY = os.environ["MAPS_API"]


def get_adr(lat, long):
    coder = geopy.GoogleV3(API_KEY)
    raw = coder.reverse([lat, long], exactly_one=True).raw
    print(raw)
    num = raw["address_components"][0]["long_name"]
    street = raw["address_components"][1]["long_name"]
    plz = raw["address_components"][-1]["long_name"]
    ort = raw["address_components"][2]["long_name"]
    return street, num, ort, plz


def get_full_adr(adr):
    coder = geopy.GoogleV3(API_KEY)
    raw = coder.geocode(adr, exactly_one=True).raw
    print(raw)
    num = raw["address_components"][0]["long_name"]
    street = raw["address_components"][1]["long_name"]
    plz = raw["address_components"][-1]["long_name"]
    ort = raw["address_components"][2]["long_name"]
    return street, num, ort, plz


if __name__ == "__main__":
    print(get_full_adr("Am Knechtacker 1, 35041"))