from lib import FILTER_DESTINATION_TYPE, FORCE_DESTINATION_TYPE, generate_rsds, get_extractions


def main():

    # set filterDestionationType to None to create RSD for *all* extractions
    extractions = get_extractions(filterDestionationType=FILTER_DESTINATION_TYPE)

    for e in extractions:

        # insert your custom logic here

        generate_rsds(e, forceHttpJsonDestination=FORCE_DESTINATION_TYPE)


if __name__ == "__main__":
    main()
