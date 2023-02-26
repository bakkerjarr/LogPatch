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
#                   - Allow different shells to be selected when executing commands.
#                   - Support package managers on different OS versions.
#                   - Handle package updates that require input from the user, such as needing to
#                     overwrite an existing configuration file.

import argparse
import logging
import subprocess
import yaml

from datetime import datetime
from jsonschema import Draft7Validator
from os import path

def datetime_now_utc():
    """Return the current datetime (UTC) following ISO 8601.

    Returns:
        str : A ISO 8601 string representation of the current datetime (UTC)
    """
    return datetime.utcnow().strftime('%Y%m%dT%H%M%S.%fZ')

def validate_schema_conf(conf) -> int:
    """Validate the schema of a deserialised YAML configuration document.
    
    Args:
        conf (dict) : The configuration that will be validated
 
    Returns:
        int         : 1 if the schema has validation errors, otherwise 0
    """
    # The description has been left in for each schema property as a form of documentation
    schema = {
        'type': 'object',
        'additionalProperties': {
            'type': 'object',
            'properties': {
                'log_directory': {
                    # 'description': "The parent directory to write log files",
                    'type': 'string'
                },
                'log_package_version_cmd': {
                    # 'description': "Set to true to log package versions before and after patching, false to not",
                    'type': 'boolean'
                },
                'log_patch_cmd':{
                    # 'description': "Set to true to log patch command output, false to not",
                    'type': 'boolean'
                },
                'name': {
                    # 'description': "The name of this recipe",
                    'type': 'string'
                },
                'patch_cmd': {
                    # 'description': "The package manager command to install patches",
                    'type': 'string'
                },
                'package_version_cmd': {
                    # 'description': "The package manager command to record package versions",
                    'type': 'string'
                }
            },
            'required': ['log_directory', 'log_package_version_cmd', 'log_patch_cmd', 'name',
                     'patch_cmd', 'package_version_cmd']
        }
    }
    validator = Draft7Validator(schema)
    errors = list(validator.iter_errors(conf))
    if len(errors) == 0:
        return 0
    for error in errors:
        logger.error("Syntax error in supplied configuration file (see below for details)\n" \
                        f"{error}")
    return 1

def subproc_Popen(cmd):
    """A helper function for executing a command and return the STDOUT and STDERR via yield.
    
    This function is based on: From https://stackoverflow.com/a/4417735

    Args:
        cmd (str) : A command to execute in a shell
    """
    popen = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             universal_newlines=True)
    for stdout_line in iter(popen.stdout.readline, ""):
        yield stdout_line
    popen.stdout.close()
    return_code = popen.wait()
    if return_code:
        raise subprocess.CalledProcessError(return_code, cmd)

def execute(cmd, log_file=''):
    """Execute a command and print the output to the terminal and optionally append to a file.
    
    Args:
        cmd (str)       : A command to execute in a shell
        log_file (str)  : The path of the file to append a command's output to
    """
    if log_file != '':
        # I'm fairly happy that the safety of 'with open...' for this program's context. Let's open
        # files in 'append' instead of 'write' mode just in case.
        with open(log_file, 'a') as f_out:
            # TODO Catch subprocess.CalledProcessError and gracefully exit the program if its caught
            for line in subproc_Popen(cmd):
                print(line, end='')
                f_out.write(line)
    else:
        for line in subproc_Popen(cmd):
            print(line, end='')

def exec_recipe(recipe):
    """Execute a LogPatch recipe.

    See the validate_schema_conf() function for information on the schema of the dict.
    
    Args:
        recipe (dict)   : The recipe to execute
    """
    logger.info(f"Executing recipe: {recipe['name']}")
    if recipe['log_package_version_cmd']:
        log_file_name = path.join(recipe['log_directory'],
                                  f"{datetime_now_utc()}_package_versions_pre-patch.log")
        execute(recipe['package_version_cmd'], log_file_name)
    if recipe['log_patch_cmd']:
        log_file_name = path.join(recipe['log_directory'],
                                  f"{datetime_now_utc()}_{recipe['name']}.log")
        execute(recipe['patch_cmd'], log_file_name)
    else:
        execute(recipe['patch_cmd'])
    if recipe['log_package_version_cmd']:
        log_file_name = path.join(recipe['log_directory'],
                                  f"{datetime_now_utc()}_package_versions_post-patch.log")
        execute(recipe['package_version_cmd'], log_file_name)

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
                            help="Path to a logpatch YAML configuration file")
    arg_parser.add_argument('recipe',
                            help="The selected recipe to use from the configuration file")
    args = arg_parser.parse_args()
    config_path = args.config_path
    selected_recipe = args.recipe

    # Ensure that the configuration file exists
    if not path.exists(config_path):
        logger.critical(f"Supplied path does not exist: {config_path}")
        exit(1)
    if not path.isfile(config_path):
        logger.critical(f"Supplied path is not a file: {config_path}")
        exit(1)
    
    # Parse the configuration file
    conf = {}
    with open(config_path, 'r') as f_in:
        try:
            conf = yaml.safe_load(f_in)
            logger.debug(conf)
        except yaml.YAMLError as excpt:
            logger.critical(f"Caught yaml.YAMLError:\n{excpt}")
            exit(1)

    # Validate the schema of the configuration file
    if validate_schema_conf(conf) != 0:
        logger.critical(f"The supplied configuration file ({config_path}) does not match the expected schema so this program must exit.")
        exit(1)
    
    # TODO Check that conf[selected_recipe]['log_directory'] exists, even if we aren't going to log anything

    try:
        exec_recipe(conf[selected_recipe])
    except subprocess.CalledProcessError as excpt:
        logger.error(f"Caught subprocess.CalledProcessError:\n{excpt}")
    
    exit(0)

# TODO Write tests to check that expected output can be gotten from commands. E.g. run `echo "Hello, World"` and check that output says "Hello, World"
