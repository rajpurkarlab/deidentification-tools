# Standard library
import argparse
import logging
from pathlib import Path

# First-party/Local

from process import deidentify_dicoms


def get_parser():

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--data_dir",
        type=str,
        default="data",
        help="Data dicrectory. If not provided, default to ./data",
    )
    parser.add_argument(
        "-log",
        "--log_level",
        type=str,
        default="ERROR",
        help="Provide logging level. Options include from INFO and ERROR",
    )

    return parser


def main():
    args = get_parser().parse_args()

    logger = logging.getLogger()
    logger.setLevel(args.log_level)

    data_folder = Path(args.data_dir)

    deidentify_dicoms(data_folder)


if __name__ == "__main__":
    main()
