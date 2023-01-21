#!/usr/bin/env python3

__author__      = "Jarrod N. Bakker"
__copyright__   = ""
__credits__     = ["Jarrod N. Bakker"]
__license__     = ""
__version__     = "0.1.0"
__maintainer__  = "Jarrod N. Bakker"
___email__      = "jarrodbakker@hotmail.com"
__status__      = "Development"
# history       : XX/12/2022 - 0.1.0 - jnb
#                 Initial version.
# future work   :
#                   - Support package managers on different OS versions.
#                   - Handle package updates that require input from the user, such as needing to
#                     overwrite an existing configuration file.

import argparse
import logging
import subprocess
import yaml

from datetime import datetime
from os import path

def subproc_Popen(cmd):
    """From https://stackoverflow.com/a/4417735"""
    popen = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             universal_newlines=True)
    for stdout_line in iter(popen.stdout.readline, ""):
        yield stdout_line 
    popen.stdout.close()
    return_code = popen.wait()
    if return_code:
        raise subprocess.CalledProcessError(return_code, cmd)

def execute(cmd, log_file=''):
    if log_file != '':
        # TODO How safe is the 'with open()...' statement below?
        with open(log_file, 'w') as f_out:
            for path in subproc_Popen(cmd):
                print(path, end='')
                f_out.write(path)
    else:
        for path in subproc_Popen(cmd):
            print(path, end='')

def exec_recipe(recipe):
    logger.info(f"Executing recipe: {recipe['name']}")
    # TODO Handle custom directory using log_directory option in config file
    if recipe['log_package_version_cmd']:
        datetime_now = datetime.now().strftime('%Y%m%dT%H%M%SZ')
        execute(recipe['package_version_cmd'],
                log_file=f"{datetime_now}_package_versions_pre-patch.log")
    if recipe['log_patch_cmd']:
        datetime_now = datetime.now().strftime('%Y%m%dT%H%M%SZ')
        execute(recipe['patch_cmd'],
                log_file=f"{datetime_now}_{recipe['name']}.log")
    else:
        execute(recipe['patch_cmd'])
    if recipe['log_package_version_cmd']:
        datetime_now = datetime.now().strftime('%Y%m%dT%H%M%SZ')
        execute(recipe['package_version_cmd'],
                log_file=f"{datetime_now}_package_versions_post-patch.log")

if __name__ == "__main__":
    LOG_LEVEL = logging.INFO
    logger = logging.getLogger(__name__)
    logger.setLevel(LOG_LEVEL)
    console = logging.StreamHandler()
    console.setLevel(LOG_LEVEL)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console.setFormatter(formatter)
    logger.addHandler(console)

    arg_parser = argparse.ArgumentParser(
                            description="Execute a software upgrade procedure using a package " \
                                        "manager. Output can optionally be recorded if " \
                                        "required. This is all controlled via a YAML file.")
    arg_parser.add_argument('config_path',
                            help="Path to a pkgptch YAML configuration file")
    arg_parser.add_argument('recipe',
                            help="The selected recipe to use from the configuration file")
    args = arg_parser.parse_args()
    config_path = args.config_path
    selected_recipe = args.recipe

    if not path.exists(config_path):
        logger.critical(f"Supplied path does not exist: {config_path}")
        exit(1)
    if not path.isfile(config_path):
        logger.critical(f"Supplied path is not a file: {config_path}")
        exit(1)
    # TODO Syntax checking of config file

    conf = {}
    with open(config_path, 'r') as f_in:
        try:
            conf = yaml.safe_load(f_in)
            logger.debug(conf)
        except yaml.YAMLError as excpt:
            logger.critical(f"Caught yaml.YAMLError:\n{excpt}")
            exit(1)

    try:
        exec_recipe(conf[selected_recipe])
    except subprocess.CalledProcessError as excpt:
        logger.error(f"Caught subprocess.CalledProcessError:\n{excpt}")
    
    exit(0)