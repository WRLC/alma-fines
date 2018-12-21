import os
import tempfile

import pytest

from fines import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    client = app.test_client()

    yield client

def test_index_redirect(client):
    '''
    GIVEN the fines app
    WHEN the index page ('/') is requested (GET)
    AND user is not logged in
    THEN the http response is 302
    '''
    r = client.get('/')
    assert r.status_code == 302

def test_login_get(client):
    '''
    GIVEN the fines app
    WHEN the index page ('/login') is requested (GET)
    AND user is not logged in
    THEN the http response is 200
    '''
    r = client.get('/login')
    assert r.status_code == 200
