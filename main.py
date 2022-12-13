import os
import json
import logging
import xml.etree.ElementTree as ET
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(".env")

XU_BASE_URL = os.getenv("XU_BASE_URL")
RSD_TEMPLATE = os.getenv("RSD_TEMPLATE")
RSD_TARGET_FOLDER = os.getenv("RSD_TARGET_FOLDER")

log = logging.getLogger()
log.setLevel(logging.INFO)


# supoprted datatypes by CData:
# string, int, double, datetime, and boolean
#
# https://cdn.cdata.com/help/DWH/ado/pg_APIinfo.htm#attr


TYPE_MAPPING = {
    "Byte": "int",
    "Short": "int",
    "Int": "int",
    "Long": "int",
    "Double": "double",
    "Decimal": "double",
    "NumericString": "string",
    "StringLengthMax": "string",
    "StringLengthUnknown": "string",
    "ByteArrayLengthExact": "string",
    "ByteArrayLengthMax": "string",
    "ByteArrayLengthUnknown": "string",
    "Date": "datetime",
    "ConvertedDate": "datetime",
    "Time": "datetime",
}


def get_extractions():

    meta_url = f"{XU_BASE_URL}/config/extractions/"

    logging.info(f"{meta_url=}")

    res = requests.get(meta_url)
    content = res.content.decode(res.apparent_encoding)
    extractions = json.loads(content).get("extractions")

    return extractions


def get_column_list(extraction_name):

    # http://localhost:8065/config/extractions/VBAK/result-columns
    meta_url = (
        f"{XU_BASE_URL}/config/extractions/{extraction_name}/result-columns"  # NOQA
    )

    res = requests.get(meta_url)
    content = res.content.decode(res.apparent_encoding)
    columns = json.loads(content).get("columns")

    return columns


def generate_rsd(extraction):

    extraction_name = extraction.get("name")
    target_file_name = Path(RSD_TARGET_FOLDER, extraction_name + ".rsd")
    extraction_url = (
        f"{XU_BASE_URL}/?name={extraction_name}" + r"&destination=http-json"
    )

    # read template RSD
    template_tree = ET.parse(RSD_TEMPLATE)

    namespaces = {
        "api": "http://apiscript.com/ns?v1",
        "xs": "http://www.w3.org/2001/XMLSchema",
        # "other": "http://apiscript.com/ns?v1",
    }

    for k, v in namespaces.items():
        ET.register_namespace(k, v)

    # set extraction URL
    template_tree.find("//api:set[@attr='URI']", namespaces).attrib[
        "value"
    ] = extraction_url

    # prepare field section to look like this:
    # <api:info title="BSEG" desc="Generated schema file."
    #      xmlns:other="http://apiscript.com/ns?v1">
    field_section = template_tree.find("//api:info", namespaces)
    field_section.clear()
    field_section.attrib["title"] = extraction_name
    field_section.attrib[
        "desc"
    ] = f"""Type: {extraction.get("type")}, Source: {extraction.get("source")}"""  # NOQA

    field_section.attrib["xmlns:other"] = "http://apiscript.com/ns?v1"

    columns = get_column_list(extraction_name)

    for c in columns:

        attributes = {
            "name": c.get("name"),
            "xs:type": TYPE_MAPPING.get(c.get("type"), "unknown"),
            "key": "true" if c.get("isPrimaryKey") else "false",
            "other:xPath": f"/json/{c.get('name')}",
            "readonly": "true",
        }

        if "length" in c.keys():
            attributes["columnsize"] = str(c.get("length"))

        if "decimalsCount" in c.keys():
            attributes["decimaldigits"] = str(c.get("decimalsCount"))

        if "description" in c.keys():
            attributes["description"] = c.get("description")

        logging.debug(c)
        logging.debug(attributes)

        field_section.append(
            ET.Element(
                "attr",
                attributes,
            )
        )

    # restore xs namespace due to malformed XML structure of RSD format
    template_tree.getroot().attrib["xmlns:xs"] = namespaces.get("xs")

    target_file_name.parent.mkdir(parents=True, exist_ok=True)

    template_tree.write(
        target_file_name,
    )


def main():

    extractions = get_extractions()

    for e in extractions:
        generate_rsd(e)


if __name__ == "__main__":
    main()
