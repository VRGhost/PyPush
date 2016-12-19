"""Main app functions."""
import os
import sys
import argparse
import logging
import logging.handlers


def get_arg_parser():
    """Argument parser for the command-line entry."""
    import PyPush

    parser = argparse.ArgumentParser(
        description="Microbot Push management daemon.")
    parser.add_argument(
        "--debug",
        default=False, action='store_true',
        help="Run in debug mode",
    )

    # Populate submodule args
    PyPush.lib.main.populate_arg_parser(parser)
    PyPush.core.main.populate_arg_parser(parser)

    subp = parser.add_subparsers(help="UI modes")
    web_ui = subp.add_parser("web_ui", help="Web forntend")
    web_ui.set_defaults(web_ui_enabled=True)
    PyPush.web.main.populate_arg_parser(web_ui)

    return parser

def setup_logging(debug):
    """Configure the logging subsystem."""
    import PyPush.core.const as const

    lvl = logging.INFO

    formatter = logging.Formatter('%(asctime)s %(module)-17s line:%(lineno)-4d %(levelname)-8s %(message)s')
    
    rotHandler = logging.handlers.RotatingFileHandler(
        os.path.join(const.TMP_DIR, "PyPush.log"),
        maxBytes=10485760,
        backupCount=5,
    )
    rotHandler.setFormatter(formatter)

    stdoutHandler = logging.StreamHandler(sys.stdout)
    stdoutHandler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(lvl)
    root_logger.addHandler(rotHandler)
    root_logger.addHandler(stdoutHandler)

def create_app(args):
    """Create the PyPush application object."""
    import PyPush
    core = PyPush.core.main.create(args.debug, args)
    mbHub = PyPush.lib.main.create(args.debug, core.getPairDb(), args)
    core.setMicrobotApi(mbHub)
    if args.web_ui_enabled:
        webUi = PyPush.web.main.create(args.debug, core, args)
        core.setDbConnection(webUi.getDbConnection())
        core.setUI(webUi)
    return core

def main(argv):
    """Main entry point into the PyPush."""
    args = get_arg_parser().parse_args(argv)
    setup_logging(args.debug)
    logging.info("====== PyPush is starting =====")
    
    try:
        app = create_app(args)
        logging.info("===== App created =====")
        app.run()
    except:
        logging.exception("Top-level exception")
        raise
    finally:
        logging.info("====== PyPush terminated ======")