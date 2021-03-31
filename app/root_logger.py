import logging
import sys


def get_logging_stdout_handler():
    logging_stdout_handler = logging.StreamHandler(sys.stdout)
    logging_stdout_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('[%(asctime)s] {%(filename)s:%(funcName)s:%(lineno)d} %(levelname)s - %(message)s','%y-%m-%d %H:%M:%S')
    logging_stdout_handler.setFormatter(formatter)
    return logging_stdout_handler


def get_root_logger():
    root_logger = logging.getLogger('root_logger')
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(get_logging_stdout_handler())
    root_logger.propagate = False
    return root_logger
