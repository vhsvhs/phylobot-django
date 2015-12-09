from portal import aws_tools
from portal.aws_tools import *
import sqlite3 as lite
import os, sys, time
import socket

DAEMONDBPATH = "job_daemon.db"

from os import listdir, environ
from django.core.exceptions import ImproperlyConfigured
def get_env_variable(var_name):
    """Get the env. variable, or return exception"""
    try:
        return environ[var_name]
    except KeyError:
        error_msg = "Set the {} environment variable".format(var_name)
        raise ImproperlyConfigured(error_msg)

S3BUCKET = get_env_variable("S3BUCKET")
SQS_JOBQUEUE_NAME = get_env_variable("SQS_JOBQUEUE_NAME")