import csv
import io
import json
import xml.etree.ElementTree as ET
from pathlib import Path

import logging

import requests
from dotenv import load_dotenv

load_dotenv(".env")

XU_BASE_URL = "http://localhost:8065"
RSD_TEMPLATE = "TEMPLATE.rsd"
RSD_TARGET_FOLDER = "./OUTPUT"

log = logging.getLogger()
log.setLevel(logging.INFO)


def get_extractions():

    res = requests.get(XU_BASE_URL)
    f = io.StringIO(res.text)
    extractions = csv.DictReader(f, delimiter=",")

    return extractions


def get_column_list(extraction_name):

    meta_url = f"{XU_BASE_URL}/metadata/?name={extraction_name}"

    res = requests.get(meta_url)
    f = io.StringIO(res.text)
    columns = csv.DictReader(f, delimiter=",")

    return columns


def generate_rsd(extraction):
    """
    sample_extraction = {
        "Name": "ODP_SalesVolumes",
        "Type": "ODP",
        "Source": "ec5",
        "Destination": "http-json",
        "LastRun": "",
        "RowCount": "",
        "LastChange": "2022-10-27_13:05:22.946",
        "Created": "2022-10-10_09:55:10.870",
    }

    sample_column = {
        "POSITION": "187",
        "NAME": "PSOO3",
        "DESC": "Description",
        "TYPE": "C",
        "LENGTH": "50",
        "DECIMALS": "0",
        "KEY": "false",
    }
    """

    target_file_name = Path(RSD_TARGET_FOLDER, extraction["Name"] + ".rsd")

    logging.info(f"{target_file_name=}")

    columns = get_column_list(extraction["Name"])

    tree = ET.parse(RSD_TEMPLATE)

    namespaces = {
        "api": "http://apiscript.com/ns?v1",
        "xs": "http://www.w3.org/2001/XMLSchema",
    }

    # <api:info title="BSEG" desc="Generated schema file." xmlns:other="http://apiscript.com/ns?v1">
    field_section = tree.find("//api:info", namespaces)

    field_section.attrib["title"] = extraction["Name"]

    # <attr name="ZBD2P" xs:type="double" readonly="false" other:xPath="/json/ZBD2P" />

    for c in columns:

        field_section.append(
            ET.Element(
                "attr",
                {
                    "xs:type": "unknown",
                    "readonly": "true",
                    "other:xPath": f"/json/{c['NAME']}",
                    "columnsize": "100",
                    "decimaldigits": "0",
                    "desc": c["DESC"],
                    "key": "true",
                },
            )
        )

        pass


def main():

    extractions = get_extractions()

    for e in extractions:

        print(e)

        generate_rsd(e)


if __name__ == "__main__":
    main()
