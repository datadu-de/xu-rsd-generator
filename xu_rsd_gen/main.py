from lib import generate_rsd, get_extractions


def main():

    # set filterDestionationType to None to create RSD for *all* extractions
    extractions = get_extractions()

    for e in extractions:
        generate_rsd(e)


if __name__ == "__main__":
    main()
