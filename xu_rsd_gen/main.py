from lib import generate_rsds, get_extractions


def main():

    # set filterDestionationType to None to create RSD for *all* extractions
    extractions = get_extractions()

    for e in extractions:
        generate_rsds(e)


if __name__ == "__main__":
    main()
