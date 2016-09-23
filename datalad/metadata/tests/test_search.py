# emacs: -*- mode: python-mode; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# -*- coding: utf-8 -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the datalad package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Some additional tests for search command (some are within test_base)"""

from mock import patch
from operator import itemgetter
from six import PY2
from datalad.api import Dataset, aggregate_metadata, install
from datalad.metadata import get_metadata_type, get_metadata
from nose.tools import assert_true, assert_equal, assert_raises
from datalad.utils import chpwd
from datalad.tests.utils import assert_in
from datalad.tests.utils import assert_is_instance
from datalad.tests.utils import assert_is_generator
from datalad.tests.utils import with_tempfile
from datalad.tests.utils import with_testsui
from datalad.support.exceptions import NoDatasetArgumentFound

from datalad.dochelpers import exc_str
import os
from os.path import join as opj
from datalad.support.exceptions import InsufficientArgumentsError
from nose import SkipTest

from datalad.api import search
from datalad.consts import LOCAL_CENTRAL_PATH
from datalad.metadata import search as search_mod

@with_testsui(interactive=False)
@with_tempfile(mkdir=True)
def test_search_outside1_noninteractive_ui(tdir):
    # we should raise an informative exception
    with chpwd(tdir):
        with assert_raises(NoDatasetArgumentFound) as cme:
            list(search("bu"))
        assert_in('UI is not interactive', str(cme.exception))


@with_tempfile(mkdir=True)
@with_tempfile(mkdir=True)
def test_search_outside1(tdir, newhome):
    with chpwd(tdir):
        # should fail since directory exists, but not a dataset
        # should not even waste our response ;)
        with patch.object(search_mod, 'LOCAL_CENTRAL_PATH', newhome):
            gen = search("bu")
            assert_is_generator(gen)
            assert_raises(NoDatasetArgumentFound, next, gen)

        # and if we point to some non-existing dataset -- the same
        assert_raises(ValueError, next, search("bu", dataset=newhome))


@with_testsui(responses='yes')
@with_tempfile(mkdir=True)
@with_tempfile()
def test_search_outside1_install_central_ds(tdir, central_dspath):
    with chpwd(tdir):
        # let's mock out even actual install/search calls
        with \
            patch.object(search_mod, 'LOCAL_CENTRAL_PATH', central_dspath), \
            patch('datalad.api.install',
                  return_value=Dataset(central_dspath)) as mock_install, \
            patch('datalad.distribution.dataset.Dataset.search',
                  new_callable=_mock_search):
            _check_mocked_install(central_dspath, mock_install)

            # now on subsequent run, we want to mock as if dataset already exists
            # at central location and then do search again
            from datalad.ui import ui
            ui.add_responses('yes')
            mock_install.reset_mock()
            with patch(
                    'datalad.distribution.dataset.Dataset.is_installed',
                    True):
                _check_mocked_install(central_dspath, mock_install)

            # and what if we say "no" to install?
            ui.add_responses('no')
            mock_install.reset_mock()
            with assert_raises(NoDatasetArgumentFound):
                list(search("bu"))

_mocked_search_results = [
    ('ds1', {'f': 'v'}),
    ('d2/ds2', {'f1': 'v1'})
]


class _mock_search(object):
    def __call__(*args, **kwargs):
        for loc, report in _mocked_search_results:
            yield loc, report


def _check_mocked_install(central_dspath, mock_install):
    gen = search(".", regex=True)
    assert_is_generator(gen)
    assert_equal(
        list(gen), [(opj(central_dspath, loc), report)
                    for loc, report in _mocked_search_results])
    mock_install.assert_called_once_with(central_dspath, source='///')

