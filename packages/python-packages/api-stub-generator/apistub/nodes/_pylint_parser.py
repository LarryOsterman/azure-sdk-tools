import inspect
import json
import logging
import os
from pylint import epylint
import re
from typing import List

_HELP_LINK_REGEX = re.compile(r"(.+) See details: *([^\s]+)")

class PylintError:

    def __init__(self, pkg_name, **kwargs):
        from apistub import DiagnosticLevel
        self.type = kwargs.pop('type', None)
        self.module = kwargs.pop('module', None)
        self.obj = kwargs.pop('obj', None)
        self.line = kwargs.pop('line', None)
        self.column = kwargs.pop('column', None)
        self.end_line = kwargs.pop('endLine', None)
        self.end_column = kwargs.pop('endColumn', None)
        self.path = kwargs.pop('path', None)
        self.symbol = kwargs.pop('symbol', None)
        self.message = kwargs.pop('message', None)
        self.message_id = kwargs.pop('message-id', None)
        self.help_link = None
        if self.path.startswith(pkg_name):
            self.path = self.path[(len(f"{pkg_name}\\\\") - 1):]
        code = self.symbol[0]
        self.level = DiagnosticLevel.ERROR if code in "EF" else DiagnosticLevel.WARNING
        self._parse_help_link()

    def _parse_help_link(self):
        try:
            (message, help_link) = _HELP_LINK_REGEX.findall(self.message)[0]
            self.message = message
            self.help_link = help_link
        except Exception as err:
            # if unable to parse, leave alone
            return
        

    def generate_tokens(self, apiview, target_id):
        apiview.add_diagnostic(obj=self, target_id=target_id)


class PylintParser:

    AZURE_CHECKER_CODE = "47"

    items: List[PylintError] = []

    @classmethod
    def _find_pylintrc(cls):
        print(os.environ)
        return os.environ["PYLINTRC_PATH"]
        # try:
        #     # prefer environment variable (necessary for tox)
        #     return os.environ["PYLINTRC_PATH"]
        # except KeyError:
        #     return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "azure_sdk_pylintrc"))


    @classmethod
    def parse(cls, path):
        from apistub import ApiView

        pkg_name = os.path.split(path)[-1]
        rcfile_path = PylintParser._find_pylintrc()
        (pylint_stdout, pylint_stderr) = epylint.py_run(f"{path} -f json --rcfile {rcfile_path}", return_std=True)
        stderr_str = pylint_stderr.read()
        # strip put stray, non-json lines from stdout
        stdout_lines = [x for x in pylint_stdout.readlines() if not x.startswith("Exception")]
        try:
            json_items = json.loads("".join(stdout_lines))
            cls.items = [PylintError(pkg_name, **x) for x in json_items if x["message-id"][1:3] == PylintParser.AZURE_CHECKER_CODE]
        except Exception as err:
            logging.error(f"Error decoding JSON: {err}")
            logging.error(f"***STDERR***\n{stderr_str}")
            raise err
        

    @classmethod
    def get_items(cls, obj) -> List[PylintError]:
        results = []
        try:
            source_file = inspect.getsourcefile(obj)
            (source_lines, start_line) = inspect.getsourcelines(obj)
            end_line = start_line + len(source_lines) - 1
        except:
            return results

        for item in cls.items:
            item_path = item.path
            if source_file.endswith(item_path):
                # only include linter warnings associated with the first line of a code block
                if item.line == start_line:
                    results.append(item)
        return results