"""Main run script for the PyPush.web."""

import argparse
import os
import sys
import logging
import logging.handlers


def populate_arg_parser(parser):
    """Argument parser for the command-line entry."""
    parser.add_argument(
        "--port",
        default=5000,
        type=int,
        help="RPC server port.")
    parser.add_argument(
        "--host",
        default="localhost",
        help="Host to bind server socket to.")
    parser.add_argument(
        "--application_root",
        default=None,
        help="Application root url."
    )
    return parser


def create(debug, core, args):
    """Main entrypoint into the program."""
    import PyPush.web
    ui = PyPush.web.ui.FlaskUI(debug, core,
        args.host, args.port,
        args.application_root,
    )
    return ui
    