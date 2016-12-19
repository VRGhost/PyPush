"""Functions related to the program initialisation - argument parsing et al."""

import argparse
import os

def populate_arg_parser(parser):
    import PyPush.core.const as const

    DB_PATH = os.path.realpath(
        os.path.join(const.TMP_DIR, "db.sqlite"))

    DB_URI = "sqlite:///{}".format(DB_PATH)

    parser.add_argument("--db_uri", default=DB_URI, help="Database URI")
    parser.add_argument(
        "--action_log",
        default=os.path.join(const.TMP_DIR, "microbot_action_log.csv"),
        help="Location of the microbot action log file",
    )
    return parser

def create(debug, args):
    """Create PyPush core using args parsed by the `populate_arg_parser` parser."""
    import PyPush.core as core
    return core.Core(
        debug, args.db_uri, args.action_log
    )