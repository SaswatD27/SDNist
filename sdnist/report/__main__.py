import json
import os
import datetime
import argparse
from pathlib import Path
from typing import Dict

from sdnist.report.common import REPORTS_DIR
import sdnist.load
from sdnist.load import data_challenge_map
from sdnist.report import \
    generate, utility_score, privacy_score,\
    ReportUIData, Dataset, ReportData
from sdnist.report.dataset import data_description
from sdnist.load import TestDatasetName

from sdnist.strs import *
from sdnist.utils import *


def run(synthetic_filepath: Path,
        output_directory: Path = REPORTS_DIR,
        test: TestDatasetName = TestDatasetName.NONE,
        data_root: Path = Path("diverse_community_excerpts_data"),
        labels_dict: Optional[Dict] = None,
        download: bool = False,
        test_mode: bool = False):
    outfile = Path(output_directory, 'report.json')
    ui_data = ReportUIData(output_directory=output_directory)
    report_data = ReportData(output_directory=output_directory)
    log = SimpleLogger()
    log.msg('SDNist: Deidentified Data Report Tool', level=0, timed=False)
    log.msg(f'Creating Evaluation Report for Deidentified Data at path: {synthetic_filepath}',
            level=1)

    if not outfile.exists():
        log.msg('Loading Datasets', level=2)
        dataset = Dataset(synthetic_filepath, log, test, data_root, download)
        ui_data = data_description(dataset, ui_data, labels_dict)
        log.end_msg()

        # Create scores
        log.msg('Computing Utility Scores', level=2)
        ui_data, report_data = utility_score(dataset, ui_data, report_data, log)
        log.end_msg()

        log.msg('Computing Privacy Scores', level=2)
        ui_data, report_data = privacy_score(dataset, ui_data, report_data, log)
        log.end_msg()

        log.msg('Saving Report Data')
        ui_data.save()
        ui_data = ui_data.data
        report_data.data['created_on'] = ui_data['Created on']
        report_data.save()
        log.end_msg()
    else:
        with open(outfile, 'r') as f:
            ui_data = json.load(f)
    log.end_msg()
    # Generate Report
    generate(ui_data, output_directory, test_mode)
    log.msg(f'Reports available at path: {output_directory}', level=0, timed=False)


class NoAction(argparse.Action):
    def __init__(self, **kwargs):
        kwargs.setdefault('default', argparse.SUPPRESS)
        kwargs.setdefault('nargs', 0)
        super(NoAction, self).__init__(**kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        pass


if __name__ == "__main__":
    bundled_datasets = {"MA": TestDatasetName.ma2019,
                        "TX": TestDatasetName.tx2019,
                        "NATIONAL": TestDatasetName.national2019}
    parser = argparse.ArgumentParser()
    parser.register('action', 'none', NoAction)
    parser.add_argument("deidentified_dataset", type=argparse.FileType("r"),
                        metavar="PATH_DEIDENTIFIED_DATASET",
                        help="Location of deidentified dataset (csv or parquet file).")
    parser.add_argument("target_dataset_name",
                        metavar="TARGET_DATASET_NAME",
                        choices=[b for b in bundled_datasets.keys()],
                        help="Select name of the target dataset "
                             "that was used to generated given deidentified dataset.")
    parser.add_argument("--labels",
                        default="",
                        help="A string with a single label"
                             "or a json file path containing multiple labels and values that "
                             "uniquely identifies deidentified data")
    parser.add_argument("--data-root", type=Path,
                        default=Path("diverse_community_excerpts_data"),
                        help="Path of the directory "
                             "to be used as the root for the target datasets.")

    group = parser.add_argument_group(title='Choices for Target Dataset Name')
    group.add_argument('[DATASET NAME]', help='[FILENAME]', action='none')
    for k, v in bundled_datasets.items():
        group.add_argument(str(k), help=f"{v.name}", action='none')

    args = parser.parse_args()

    if not REPORTS_DIR.exists():
        os.mkdir(REPORTS_DIR)
    TARGET_DATA = bundled_datasets[args.target_dataset_name]
    target_name = TARGET_DATA.name

    # create directory for current report run
    time_now = datetime.datetime.now().strftime('%m-%d-%YT%H.%M.%S')

    this_report_dir = Path(REPORTS_DIR, f'{target_name}_{time_now}')

    if not this_report_dir.exists():
        os.mkdir(this_report_dir)

    # check if labels are given by the user
    labels = args.labels

    # if labels are input by the user
    if len(labels):
        # if labels is a path to a json file then load it as dictionary
        if str(labels).endswith('.json'):
            with open(labels, 'r') as fp:
                labels = json.load(fp)
        # if labels is a string then add label as a value to key named label
        # in a dictionary
        else:
            labels = {'label': labels}
    else:
        labels = None

    input_cnf = {
        TEST: TARGET_DATA,
        SYNTHETIC_FILEPATH: Path(args.deidentified_dataset.name),
        DATA_ROOT: Path(args.data_root),
        OUTPUT_DIRECTORY: this_report_dir,
        LABELS_DICT: labels,
        DOWNLOAD: True,
    }

    run(**input_cnf)
