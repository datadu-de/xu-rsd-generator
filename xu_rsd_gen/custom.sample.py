from .main import generate_rsd, get_extractions
from .lib import FILTER_DESTINATION_TYPE, FORCE_DESTINATION_TYPE


def main():

    # set filterDestionationType to None to create RSD for *all* extractions
    extractions = get_extractions(filterDestionationType=FILTER_DESTINATION_TYPE)

    for e in extractions:

        # insert your custom logic here

        generate_rsd(e, forceHttpJsonDestination=FORCE_DESTINATION_TYPE)


if __name__ == "__main__":
    main()
