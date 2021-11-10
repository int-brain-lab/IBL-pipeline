"""IBL populate routines

Run different DataJoint populate functions for ingesting IBL data. Requires a valid
connection to a database as well as an existing connection to Alyx. The script will
run the function `task_runner` and requires the following modules:

    ibl_pipeline.ingest.job
    ibl_pipeline.process.populate_behavior
    ibl_pipeline.process.populate_ephys
    ibl_pipeline.process.populate_wheel

Usage as a script:

    python populate.py [OPTIONS]...

See script help messages:

    python populate.py --help
"""

import argparse
import sys


def parse_args(args: list[str]) -> argparse.Namespace:
    """
    Parse command line parameters

    :param args: Command line parameters as list of strings (for example  `["--help"]`)
    :type args: list[str]
    :return: A Namespace of command line parameters
    :rtype: argparse.Namespace
    """

    class ArgumentDefaultsRawDescriptionHelpFormatter(
        argparse.ArgumentDefaultsHelpFormatter, argparse.RawDescriptionHelpFormatter
    ):
        pass

    class MultipyArg(argparse.Action):
        def __init__(self, option_strings, multiplier=1, *args, **kwargs):
            self.mult = multiplier
            super(MultipyArg, self).__init__(
                option_strings=option_strings, *args, **kwargs
            )

        def __call__(self, parser, namespace, values, option_string=None):
            setattr(namespace, self.dest, self.mult * values if values > 0 else values)

    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=ArgumentDefaultsRawDescriptionHelpFormatter
    )

    parser.add_argument(
        "task",
        help="The type of ingestion task to run.",
        type=str,
        choices=["ingest", "behavior", "wheel", "ephys"],
    )

    parser.add_argument(
        "-d",
        "--duration",
        dest="run_duration",
        help="Specify the length of time for which to run the task (in hours). "
        "A negative duration will run in an infinite loop. ",
        type=float,
        default=-1,
        action=MultipyArg,
        multiplier=3600,
    )

    parser.add_argument(
        "-s",
        "--sleep",
        dest="sleep_duration",
        help="Time to sleep in between loops (in minutes)",
        type=float,
        default=1,
        action=MultipyArg,
        multiplier=60,
    )

    parser.add_argument(
        "-b",
        "--backtrack",
        dest="backtrack_days",
        help="The number of past days for which to compare records. ",
        type=int,
        default=3,
    )

    parser.add_argument(
        "-x",
        "--xtable",
        dest="excluded_tables",
        help="Exclude a behavior table. Can be used multiple times. ",
        nargs="+",
        type=str,
        action='extend'
    )

    parser.add_argument(
        "--xplots",
        dest="exclude_plottings",
        help="Exclude populating plots from module 'ibl_pipeline.plotting.ephys'. ",
        action="store_true"
    )

    return parser.parse_args(args)


def task_runner(task: str, **kwargs) -> None:
    """
    Main function to run ingestion task from the available task types

    :param task: Name of task to run
    :type task: str
    :raises ValueError: Task type not implemented
    """
    from ibl_pipeline.ingest import job
    from ibl_pipeline.process import populate_behavior, populate_ephys, populate_wheel

    if task == "ingest":
        job.populate_ingestion_tables(**kwargs)
    elif task == "behavior":
        populate_behavior.main(**kwargs)
    elif task == "wheel":
        populate_wheel.main(**kwargs)
    elif task == "ephys":
        populate_ephys.main(**kwargs)
    else:
        raise NotImplementedError(
            f"The task '{task}' is not implemented. "
            "Run the script help documentation to see the valid options: "
            "python populate.py --help"
        )


def main(args: list[str]) -> None:
    """
    Wrapper allowing worker functions to be called from CLI

    :param args: command line parameters as list of strings (for example  ``["--help"]``)
    :type args: list[str]
    """
    arg_ns = parse_args(args)
    kwargs = dict((a, v) for a, v in vars(arg_ns).items() if a != "task")
    task_runner(arg_ns.task, **kwargs)


def run() -> None:
    """
    Calls :func:`main` passing the CLI arguments extracted from `sys.argv`

    This function can be used as entry point to create console scripts with setuptools.
    """
    main(sys.argv[1:])


if __name__ == "__main__":
    run()
