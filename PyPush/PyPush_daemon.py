"""This is start-up script for the web UI in the daemon mode."""

import os
import sys
import datetime

import daemon
import lockfile

import PyPush.web

def get_arg_parser():
    """Argument parser for the command-line entry."""
    
    tmpDir = PyPush.web.const.TMP_DIR

    parser = PyPush.web.main.get_arg_parser()
    parser.add_argument("--working_directory", default=tmpDir, 
        help="Location of the working directory of the daemon")
    parser.add_argument("--pidfile",
        default=os.path.join(tmpDir, "pyPush.pid"),
        help="Location of the pidfile")
    parser.add_argument("--stdout",
        default=os.path.join(tmpDir, "pyPush_stdout.txt"))
    parser.add_argument("--stderr",
        default=os.path.join(tmpDir, "pyPush_stderr.txt"))
    parser.add_argument("--command",
        default="status", choices=("status", "start", "stop"),
        help="Deamon management command."
    )
    return parser

def open_io_redirect_file(fname):
    fobj = open(fname, "w")
    fobj.write("\n\n\n===== {} =====\n\n\n".format(
        datetime.datetime.now().isoformat()
    ))
    return fobj

def run_daemon(args):
    ctx = daemon.DaemonContext(
        working_directory=args.working_directory,
        pidfile=lockfile.LockFile(args.pidfile),
        stdout=open_io_redirect_file(args.stdout),
        stderr=open_io_redirect_file(args.stderr),
    )
    if args.command == "status":
        sys,exit(1 if ctx.is_open else 0) 
    elif args.command == "stop":
        ctx.close()
    elif args.command == "start":
        with ctx:
            PyPush.web.main.main(
                False, # I hereby force debug-less mode on the daemon.
                args.host, args.port,
                args.db_uri,
                args.ble_driver, args.ble_device
            )
    else:
        raise Exception("Unexpected daemon command {!r}".format(args.command))

if __name__ == "__main__":
    args = get_arg_parser().parse_args()
    run_daemon(args)