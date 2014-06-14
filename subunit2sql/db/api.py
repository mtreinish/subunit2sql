# Copyright 2014 Hewlett-Packard Development Company, L.P.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from oslo.config import cfg
from oslo.db.sqlalchemy import session as db_session
from oslo.db.sqlalchemy import utils as db_utils

from subunit2sql.db import models
from subunit2sql import exceptions

CONF = cfg.CONF

DAY_SECONDS = 60 * 60 * 24

_FACADE = None


def _create_facade_lazily():
    global _FACADE
    if _FACADE is None:
        _FACADE = db_session.EngineFacade(
            CONF.database.connection,
            **dict(CONF.database.iteritems()))
    return _FACADE


def get_session(autocommit=True, expire_on_commit=False):
    facade = _create_facade_lazily()
    return facade.get_session(autocommit=autocommit,
                              expire_on_commit=expire_on_commit)


def create_test(test_id, run_count=0, success=0, failure=0):
    """Create a new test record in the database

    :param test_id: test_id identifying the test
    :param run_count: total number or runs
    :param success: number of successful runs
    :param failure: number of failed runs

    Raises InvalidRunCount if the run_count doesn't equal the sum of the
    successes and failures.
    """
    if run_count != success + failure:
        raise exceptions.InvalidRunCount()
    test = models.Test()
    test.test_id = test_id
    test.run_count = run_count
    test.success = success
    test.failure = failure
    session = get_session()
    with session.begin():
        session.add(test)
    return test


def create_run(skips=0, fails=0, passes=0, run_time=0, artifacts=None):
    """Create a new run record in the database

    :param skips: total number of skiped tests
    :param fails: total number of failed tests
    :param passes: total number of passed tests
    :param run_time: total run time
    :param artifacts: A link to any artifacts from the test run
    """
    run = models.Run()
    run.skips = skips
    run.fails = fails
    run.passes = passes
    run.run_time = run_time
    if artifacts:
        run.artifacts = artifacts
    session = get_session()
    with session.begin():
        session.add(run)
    return run


def create_test_run(test_id, run_id, status, start_time=None,
                    end_time=None):
    """Create a new test run record in the database

    :param test_id: uuid for test that was run
    :param run_id: uuid for run that this was a member of
    :param start_time: when the test was started
    :param end_time: when the test was finished
    """
    test_run = models.TestRun()
    test_run.test_id = test_id
    test_run.run_id = run_id
    test_run.end_time = end_time
    test_run.start_time = start_time
    session = get_session()
    with session.begin():
        session.add(test_run)
    return test_run


def get_all_tests():
    query = db_utils.model_query(models.Test)
    return query.all()


def get_all_runs():
    query = db_utils.models_query(models.Run)
    return query.all()


def get_all_test_runs():
    query = db_utils.models_query(models.TestRun)
    return query.all()


def get_test_by_id(id, session=None):
    session = session or get_session()
    test = db_utils.models_query(models.Test, session).filter_by(
        id=id).first()
    return test


def get_test_by_test_id(test_id, session=None):
    session = session or get_session()
    test = db_utils.models_query(models.Test, session).filter_by(
        test_id=test_id).first()
    return test


def get_test_run_by_id(test_run_id, session=None):
    session = session or get_session()
    test_run = db_utils.model_query(models.TestRun, session=session).filter_by(
        id=test_run_id).first()
    return test_run


def get_test_runs_by_test_id(test_id, session=None):
    session = session or get_session()
    test_runs = db_utils.model_query(models.TestRun,
                                     session=session).filter_by(
        test_id=test_id).all()
    return test_runs


def get_test_runs_by_run_id(run_id, session=None):
    session = session or get_session()
    test_runs = db_utils.model_query(models.Run, session=session).filter_by(
        run_id=run_id).all()
    return test_runs


def get_test_run_duration(test_run_id):
    session = get_session()

    test_run = get_test_run_by_id(test_run_id, session)
    start = test_run.start_time
    end = test_run.end_time
    if not start or not end:
        duration = ''
    else:
        delta = end - start
        duration = '%d.%06ds' % (
            delta.days * DAY_SECONDS + delta.seconds, delta.microseconds)
    return duration