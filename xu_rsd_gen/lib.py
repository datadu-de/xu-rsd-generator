import datetime
import json
import logging
import os
import xml.etree.ElementTree as ET
from pathlib import Path

import requests
from dotenv import load_dotenv

logging.basicConfig(filename="debug.log", filemode="w", level=logging.DEBUG)

load_dotenv()


XU_BASE_URL = os.getenv("XU_BASE_URL", "http://localhost:8065")
RSD_TEMPLATE = os.getenv("RSD_TEMPLATE", "TEMPLATE_JSON.rsd")
RSD_TARGET_FOLDER = os.getenv("RSD_TARGET_FOLDER", "./OUTPUT")
FILTER_DESTINATION_TYPE = os.getenv("FILTER_DESTINATION_TYPE", "HTTPJSON")
DESTINATION_TYPE_PARAMETER = os.getenv("DESTINATION_TYPE_PARAMETER", "http-json")
FORCE_DESTINATION_TYPE = os.getenv("FORCE_DESTINATION_TYPE", "False").lower() in (
    "true",
    "1",
)
DEFAULT_DAYS_SLIDING_WINDOW = int(os.getenv("DEFAULT_DAYS_SLIDING_WINDOW", 3))

# logging variables to output progress
RUN_EXTRACTIONS = 0
TOTAL_EXTRACTIONS = 0

SLIDING_COLUMNS = json.loads(
    os.getenv(
        "SLIDING_COLUMNS",
        '["AEDAT"]',
    )
)


required_globals = [
    "XU_BASE_URL",
    "RSD_TEMPLATE",
    "RSD_TARGET_FOLDER",
    "FILTER_DESTINATION_TYPE",
    "DESTINATION_TYPE_PARAMETER",
    "FORCE_DESTINATION_TYPE",
]

k, v = "", ""
for k, v in globals().items():
    if k in required_globals:
        logging.info((k, v))


# supoprted data types by CData:
# string, int, double, datetime, and boolean
#
# decimals are implicitly supported by specifying columnsize (precision) and decimaldigits(scale)
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
    "Decimal": "decimal",
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


def get_extractions(filterDestionationType=FILTER_DESTINATION_TYPE):
    meta_url = f"{XU_BASE_URL}"

    if (
        filterDestionationType is not None
        and filterDestionationType in DESTINATION_TYPES
    ):
        params = {"destinationType": filterDestionationType}
    else:
        params = {}

    logging.info(f"{meta_url=}")

    res = requests.get(meta_url, params=params)
    content = res.content.decode(res.apparent_encoding)
    extractions = json.loads(content).get("extractions")

    logging.info(f"{extractions=}")

    # log extractions found:
    global TOTAL_EXTRACTIONS
    TOTAL_EXTRACTIONS = len(extractions)
    print("Extractions Found: " + str(TOTAL_EXTRACTIONS))

    return extractions


def get_column_list(extraction_name):
    # http://localhost:8065/config/extractions/VBAK/result-columns
    meta_url = f"{XU_BASE_URL}/config/extractions/{extraction_name}/result-columns"

    logging.info(f"{meta_url=}")

    res = requests.get(meta_url)
    content = res.content.decode(res.apparent_encoding)

    logging.info(f"Raw columns of extraction '{extraction_name}'")
    logging.info(f"{content=}")

    columns = json.loads(content).get("columns")

    logging.info(f"Decoded columns of extraction '{extraction_name}'")
    logging.info(f"{columns=}")

    return columns


def get_parameters(extraction_name):
    # http://localhost:8065/config/extractions/plants/parameters/
    meta_url = f"{XU_BASE_URL}/config/extractions/{extraction_name}/parameters"

    logging.info(f"{meta_url=}")

    res = requests.get(meta_url)
    content = res.content.decode(res.apparent_encoding)
    parameters = json.loads(content).get("custom")

    logging.info(f"{parameters=}")

    return parameters


def generate_rsd(
    extraction, filename, extraction_url, forceDestinationType=FORCE_DESTINATION_TYPE
):
    extraction_name = extraction.get("name")
    columns = get_column_list(extraction_name)

    # read template RSD
    template_tree = ET.parse(RSD_TEMPLATE)

    namespaces = {
        "api": "http://apiscript.com/ns?v1",
        "xs": "http://www.w3.org/2001/XMLSchema",
    }

    for k, v in namespaces.items():
        ET.register_namespace(k, v)

    # set extraction URL
    template_tree.find(".//api:set[@attr='URI']", namespaces).attrib[
        "value"
    ] = extraction_url

    # prepare field section to look like this:
    # <api:info title="BSEG" desc="Generated schema file."
    #      xmlns:other="http://apiscript.com/ns?v1">
    field_section = template_tree.find(".//api:info", namespaces)
    field_section.clear()
    field_section.attrib["title"] = extraction_name
    field_section.attrib["desc"] = (
        f"""Type: {extraction.get("type")}, Source: {extraction.get("source")}"""
    )

    field_section.attrib["xmlns:other"] = "http://apiscript.com/ns?v1"

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

        logging.info(f"{c=}")
        logging.info(f"{attributes=}")

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

    if hasattr(ET, "indent"):
        ET.indent(template_tree)
    else:
        logging.warning(
            f"""Could not apply XML intendation to "{filename}". (only available with Python >= 3.9)"""
        )

    filename.parent.mkdir(parents=True, exist_ok=True)

    template_tree.write(
        filename,
    )


def generate_rsds(
    extraction,
    forceDestinationType=FORCE_DESTINATION_TYPE,
    slidingDays=DEFAULT_DAYS_SLIDING_WINDOW,
):
    extraction_name = extraction.get("name")
    columns = get_column_list(extraction_name)

    extraction_base_url = f"{XU_BASE_URL}/run/{extraction_name}/?" + (
        f"&destination={DESTINATION_TYPE_PARAMETER}" if forceDestinationType else ""
    )

    extraction_urls = {
        Path(RSD_TARGET_FOLDER, extraction_name + ".rsd"): extraction_base_url
    }

    for c in columns:
        column_name = c.get("name")
        if column_name in SLIDING_COLUMNS:
            extraction_urls[
                Path(
                    RSD_TARGET_FOLDER,
                    extraction_name + f"_sliding_{column_name}_{slidingDays}days.rsd",
                )
            ] = extraction_base_url + (
                "".join(
                    (
                        f"""&where={column_name}%20%3E=%20%27""",
                        (
                            datetime.date.today() - datetime.timedelta(slidingDays)
                        ).strftime(r"%Y%m%d"),
                        r"%27",
                    )
                )
            )

    # log extraction generation:
    global RUN_EXTRACTIONS
    RUN_EXTRACTIONS = RUN_EXTRACTIONS + 1
    slidingCounter = 0

    for filename, extraction_url in extraction_urls.items():

        # print log to io:
        print(
            "("
            + str(RUN_EXTRACTIONS)
            + "_"
            + str(slidingCounter)
            + "/"
            + str(TOTAL_EXTRACTIONS)
            + ") "
            + "\tGenerating RSD for: "
            + extraction_name
        )
        slidingCounter += 1

        generate_rsd(
            extraction,
            filename,
            extraction_url,
            forceDestinationType=FORCE_DESTINATION_TYPE,
        )
