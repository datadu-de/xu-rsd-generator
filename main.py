import csv
import io
import json
import xml

import requests

XU_BASE_URL = "http://localhost:8065/"
RSD_TEMPLATE = "TEMPLATE.rsd"
RSD_TARGET_FOLDER = "."


def get_extractions():
    res = requests.get(XU_BASE_URL)
    f = io.StringIO(res.text)
    extractions = csv.DictReader(f, delimiter=",")

    return extractions


def generate_rsd(extraction):
    


def main():
    extractions = get_extractions()

    for e in extractions:
        generate_rsd(e)


if __name__ == "__main__":
    main()
