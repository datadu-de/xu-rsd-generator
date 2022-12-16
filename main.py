import json
import logging
import os
import xml.etree.ElementTree as ET
from pathlib import Path

import requests
from dotenv import load_dotenv

logging.basicConfig(filename="debug.log", filemode="w", level=logging.DEBUG)

load_dotenv(".env")

XU_BASE_URL = os.getenv("XU_BASE_URL", "http://localhost:8065")
RSD_TEMPLATE = os.getenv("RSD_TEMPLATE", "TEMPLATE.rsd")
RSD_TARGET_FOLDER = os.getenv("RSD_TARGET_FOLDER", "./OUTPUT")
FILTER_DESTINATION_TYPE = os.getenv("FILTER_DESTINATION_TYPE", "HTTPJSON")
FORCE_HTTP_JSON_DESTINATION = os.getenv("FORCE_HTTP_JSON_DESTINATION", "False").lower() in ("true", "1")


# supoprted data types by CData:
# string, int, double, datetime, and boolean
#
# data types by Xtract Universal:
# Byte, Short, Int, Long, Double, Decimal, NumericString, StringLengthMax,
# StringLengthUnknown, ByteArrayLengthExact, ByteArrayLengthMax,
# ByteArrayLengthUnknown, Date, ConvertedDate, Time
#
# <https://cdn.cdata.com/help/DWH/ado/pg_APIinfo.htm#attr>
# <https://help.theobald-software.com/en/xtract-universal/advanced-techniques/metadata-access-via-http-json#result-columns-of-an-extraction>
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


# destination types available in Xtract Universal
# <https://help.theobald-software.com/en/xtract-universal/advanced-techniques/metadata-access-via-http-json#list-of-extractions-with-a-specific-destination-type>
DESTINATION_TYPES = [
    "Unknown",
    "Alteryx",
    "AlteryxConnect",
    "AzureDWH",
    "AzureBlob",
    "CSV",
    "DB2",
    "EXASOL",
    "FileCSV",
    "FileJSON",
    "GoodData",
    "GoogleCloudStorage",
    "HANA",
    "HTTPJSON",
    "MicroStrategy",
    "MySQL",
    "ODataAtom",
    "Oracle",
    "Parquet",
    "PostgreSQL",
    "PowerBI",
    "PowerBIConnector",
    "Qlik",
    "Redshift",
    "S3Destination",
    "Salesforce",
    "SharePoint",
    "Snowflake",
    "SQLServer",
    "SqlServerReportingServices",
    "Tableau",
    "Teradata",
    "Vertica",
]


def get_extractions(filterDestionationType=None):

    meta_url = f"{XU_BASE_URL}/config/extractions/"

    if filterDestionationType is not None and filterDestionationType in DESTINATION_TYPES:
        params = {"destinationType": filterDestionationType}
    else:
        params = {}

    logging.info(f"{meta_url=}")

    res = requests.get(meta_url, params=params)
    content = res.content.decode(res.apparent_encoding)
    extractions = json.loads(content).get("extractions")

    logging.debug(extractions)

    return extractions


def get_column_list(extraction_name):

    # http://localhost:8065/config/extractions/VBAK/result-columns
    meta_url = f"{XU_BASE_URL}/config/extractions/{extraction_name}/result-columns"

    logging.info(f"{meta_url=}")

    res = requests.get(meta_url)
    content = res.content.decode(res.apparent_encoding)
    columns = json.loads(content).get("columns")

    return columns


def get_parameters(extraction_name):

    # http://localhost:8065/config/extractions/plants/parameters/
    meta_url = f"{XU_BASE_URL}/config/extractions/{extraction_name}/parameters"

    logging.info(f"{meta_url=}")

    res = requests.get(meta_url)
    content = res.content.decode(res.apparent_encoding)
    parameters = json.loads(content).get("custom")

    logging.debug(parameters)

    return parameters


def generate_rsd(extraction, forceHttpJsonDestination=False):

    extraction_name = extraction.get("name")
    target_file_name = Path(RSD_TARGET_FOLDER, extraction_name + ".rsd")
    extraction_url = (
        f"""{XU_BASE_URL}/?name={extraction_name}{"&destination=http-json" if forceHttpJsonDestination else ""}"""
    )

    # read template RSD
    template_tree = ET.parse(RSD_TEMPLATE)

    namespaces = {"api": "http://apiscript.com/ns?v1", "xs": "http://www.w3.org/2001/XMLSchema"}

    for k, v in namespaces.items():
        ET.register_namespace(k, v)

    # set extraction URL
    template_tree.find(".//api:set[@attr='URI']", namespaces).attrib["value"] = extraction_url

    # prepare field section to look like this:
    # <api:info title="BSEG" desc="Generated schema file."
    #      xmlns:other="http://apiscript.com/ns?v1">
    field_section = template_tree.find(".//api:info", namespaces)
    field_section.clear()
    field_section.attrib["title"] = extraction_name
    field_section.attrib["desc"] = f"""Type: {extraction.get("type")}, Source: {extraction.get("source")}"""

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

    # to be implemented for sliding window automation
    # parameters = get_parameters(extraction_name)

    # if parameters is not None:
    #     pass

    # restore xs namespace due to malformed XML structure of RSD format
    template_tree.getroot().attrib["xmlns:xs"] = namespaces.get("xs")

    try:
        ET.indent(template_tree)
    except AttributeError:
        logging.warning(
            f"""Could not apply XML intendation to "{target_file_name}". (only available with Python >= 3.9)"""
        )

    target_file_name.parent.mkdir(parents=True, exist_ok=True)

    template_tree.write(
        target_file_name,
    )


def main():

    # set filterDestionationType to None to create RSD for *all* extractions
    extractions = get_extractions(filterDestionationType=FILTER_DESTINATION_TYPE)

    for e in extractions:
        generate_rsd(e, forceHttpJsonDestination=FORCE_HTTP_JSON_DESTINATION)


if __name__ == "__main__":
    main()
