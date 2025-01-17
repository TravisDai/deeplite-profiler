from collections import OrderedDict
import logging

from .metrics import Comparative, compare_status_values, Metric


class _LoggerHolder:
    """
    Holds the logger for the profiler module and redirect any calls made to its held logger. If none is held
    then defaults to logging.getLogger('deeplite_profiler'). This allows customization of the logging
    being used in the profiler by an external library by importing setLogger.
    """
    __singleton = False

    def __new__(cls, *args, **kwargs):
        if cls.__singleton:
            raise TypeError("This class is a singleton!")
        cls.__singleton = True
        return super().__new__(cls)

    def __init__(self):
        self._logger = None

    @property
    def logger(self):
        if self._logger is None:
            self._logger = logging.getLogger('deeplite_profiler')
            self._logger.debug("Defaulting to logging.getLogger('deeplite_profiler')'s logger")
        return self._logger

    @logger.setter
    def logger(self, new_logger):
        self._logger = new_logger
        self._logger.debug("Profiler's logger set to {}".format(new_logger))

    def __getattribute__(self, item):
        if item in ('logger', '_logger'):
            return object.__getattribute__(self, item)
        return getattr(self.logger, item)
_logger_holder = _LoggerHolder()


# silence the name for now
def getLogger(name=None):
    """
    Returns an instance of _LoggerHolder. Even though the name is misleading, any code using this return value
    should use it as if it was a logger. This enables to dynamically change the logger of the library after
    the modules were loaded and their logger declared in their headers.
    """
    return _logger_holder


def setLogger(logger):
    _logger_holder.logger = logger


class NotComputedValue:
    def __format__(self, format_spec):
        s = '<NotComputed>'
        if '>' in format_spec:
            format_spec = format_spec.split('>')[-1]
            if '.' in format_spec:
                format_spec = format_spec.split('.')[0]
            if format_spec.isdigit():
                s = ' ' * max(int(format_spec) - len(s), 0) + s
        return s

    def __repr__(self):
        return '<NotComputed>'

    def __str__(self):
        return '<NotComputed>'


def parse_metric(metric):
    text = metric.friendly_name()
    if metric.value is None:
        value = NotComputedValue()
        units = ''
        comparative = Comparative.NONE
    else:
        value = metric.get_value()
        units = metric.get_units()
        units = '' if units is None else units
        comparative = metric.get_comparative()
    description = metric.description()
    return text, value, units, comparative, description


def make_one_model_summary_str(status_dict, short_print=True, description_str='', summary_str='\n'):
    line_length, col1_length, col2_length = 63, 40, 20
    summary_str += "+" + "-" * line_length + "+" + "\n"
    line_new = "|{:^{line_length}}|".format("Deeplite Profiler", line_length=line_length)
    summary_str += line_new + "\n"
    summary_str += "+" + "-" * (col1_length + 1) + "+" + "-" * (col2_length + 1) + "+" + "\n"
    line_new = "|{:>{col1_length}} | {:>{col2_length}}|".format("Param Name (" + status_dict['name'] + ")",
                                                                "Value", col1_length=col1_length,
                                                                col2_length=col2_length)
    summary_str += line_new + "\n"
    line_new = "|{:>{col1_length}} | {:>{col2_length}}|".format("Backend: " + status_dict['backend'], "",
                                                                col1_length=col1_length,
                                                                col2_length=col2_length)
    summary_str += line_new + "\n"
    summary_str += "+" + "-" * (col1_length + 1) + "+" + "-" * (col2_length + 1) + "+" + "\n"

    for status in status_dict.values():
        if not isinstance(status, Metric):
            continue
        text, value, units, _, desc = parse_metric(status)
        print_str = text + ' (' + units + ')'
        line_new = "|{0:>{col1_length}} | {1:>{col2_length}.4f}|".format(print_str, value,
                                                                         col1_length=col1_length,
                                                                         col2_length=col2_length)
        summary_str += line_new + "\n"
        description_str += '* ' + text + ': ' + desc + "\n"
    summary_str += "+" + "-" * (col1_length + 1) + "+" + "-" * (col2_length + 1) + "+" + "\n"

    if not short_print:
        # Creating footnote
        summary_str += "Note: " + "\n"
        summary_str += description_str
        summary_str += "+" + "-" * line_length + "+"

    return summary_str


def make_two_models_summary_str(status_dict, status_dict_2, short_print=True, description_str='',
                                summary_str='\n'):
    line_length, col0_length, col1_length, col2_length, col3_length = 122, 40, 25, 25, 25
    summary_str += "+" + "-" * line_length + "+" + "\n"
    line_new = "|{:^{line_length}}|".format("Deeplite Profiler", line_length=line_length)
    summary_str += line_new + "\n"
    summary_str += "+" + "-" * (col0_length + 1) + "+" + "-" * (col1_length + 1) + "+" + "-" * (
            col2_length + 1) + "+" + "-" * (col2_length + 1) + "+" + "\n"
    line_new = "|{:>{col0_length}} | {:>{col1_length}}| {:>{col2_length}}| {:>{col3_length}}|".format(
        "Param Name", "Enhancement", "Value (" + status_dict['name'] + ")",
                                     "Value (" + status_dict_2['name'] + ")", col0_length=col0_length,
        col1_length=col1_length,
        col2_length=col2_length, col3_length=col3_length)
    summary_str += line_new + "\n"
    line_new = "|{:>{col0_length}} | {:>{col1_length}}| {:>{col2_length}}| {:>{col3_length}}|".format(
        "", "", "Backend: " + status_dict['backend'], "Backend: " + status_dict_2['backend'],
        col0_length=col0_length, col1_length=col1_length, col2_length=col2_length, col3_length=col3_length)
    summary_str += line_new + "\n"
    summary_str += "+" + "-" * (col0_length + 1) + "+" + "-" * (col1_length + 1) + "+" + "-" * (
            col2_length + 1) + "+" + "-" * (col2_length + 1) + "+" + "\n"

    for sk, sv in status_dict.items():
        if sk in status_dict_2 and isinstance(sv, Metric):
            sv2 = status_dict_2[sk]
            text, value_1, units_1, comp, desc = parse_metric(sv)
            _, value_2, units_2, _, _ = parse_metric(sv2)

            if comp is None:
                comp = Comparative.NONE

            if units_1 != "" and units_2 != "" and units_1 != units_2:
                # TODO fix when units are not the same
                val = "<Unsupported units>"
            else:
                try:
                    # this should raise a ValueError if the str is not correct
                    if isinstance(comp, str):
                        comp = Comparative(comp)
                    rval = compare_status_values(comp, value_1, value_2)
                except ZeroDivisionError:
                    val = "INF"
                except ValueError:
                    val = "<Error Comparing>"
                else:
                    if rval is None:
                        val = '---'
                    else:
                        format_str = "{:>.2f}"
                        if comp is not Comparative.DIFF:
                            format_str += "x"
                        val = format_str.format(rval)

            print_str = text + ' (' + units_1 + ')'
            line_new = "|{:>{col0_length}} | {:>{col1_length}}| {:>{col2_length}.4f}| {:>{col3_length}.4f}|".format(
                print_str, val, value_1, value_2,
                col0_length=col0_length, col1_length=col1_length, col2_length=col2_length,
                col3_length=col3_length)
            summary_str += line_new + "\n"
            description_str += '* ' + text + ': ' + desc + "\n"
    summary_str += "+" + "-" * (col0_length + 1) + "+" + "-" * (col1_length + 1) + "+" + "-" * (
            col2_length + 1) + "+" + "-" * (col2_length + 1) + "+" + "\n"

    # Creating footnote
    if not short_print:
        summary_str += "Note: " + "\n"
        summary_str += description_str
        summary_str += "+" + "-" * line_length + "+"

    return summary_str


def default_display_filter_function(status_dict):
    """
    The default order is like:
        - Evaluation Metric
        - Model Size
        - Computational Complexity
        - Number of Parameters
        - Memory Footprint
        - Execution Time
        - Any other custom Metric

    Remove 'Inference Time' as it is not a super relevant metric to display
    """
    order = ('eval_metric', 'model_size', 'flops', 'total_params', 'memory_footprint', 'execution_time')
    leftovers = tuple(set(status_dict.keys()) - set(('inference_time',) + order))
    order = order + leftovers

    new_status_dict = OrderedDict()
    for k in order:
        if k in status_dict:
            new_status_dict[k] = status_dict[k]

    return new_status_dict
