from main import FILTER_DESTINATION_TYPE, FORCE_HTTP_JSON_DESTINATION, generate_rsd, get_extractions


def main():

    # set filterDestionationType to None to create RSD for *all* extractions
    extractions = get_extractions(filterDestionationType=FILTER_DESTINATION_TYPE)

    for e in extractions:

        # insert your custom logic here

        generate_rsd(e, forceHttpJsonDestination=FORCE_HTTP_JSON_DESTINATION)


if __name__ == "__main__":
    main()
