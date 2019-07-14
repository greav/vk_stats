import pytest
import mock
from app import app


@pytest.fixture(scope='module')
def client():
    app.config['TESTING'] = True

    with app.test_client() as client:
        yield client


def download_data(client, id_, date, post_id_checked, text_checked, attachments_checked, n_attachments_checked,
                  n_likes_checked, n_reposts_checked, n_comments_checked):
    """
    helper function for download post form
    """
    return client.post('/download/data.csv', data=dict(
        id_=id_, date=date, post_id_checked=post_id_checked, text_checked=text_checked,
        attachments_checked=attachments_checked, n_attachments_checked=n_attachments_checked,
        n_likes_checked=n_likes_checked, n_reposts_checked=n_reposts_checked, n_comments_checked=n_comments_checked
    ), follow_redirects=True)


def test_empty_checkbuttons(client):
    """
    check if no options have been selected
    """
    response = download_data(client, id_='greav_t', date='2019-01-15', post_id_checked=None, text_checked=None,
                             attachments_checked=None, n_attachments_checked=None, n_likes_checked=None,
                             n_reposts_checked=None, n_comments_checked=None)
    assert b'You should choose at least one of the options above' in response.data


def test_n_attachments(client):
    """
    check if number of attachments option has been selected and attachments option haven't been selected
    """
    response = download_data(client, id_='greav_t', date='2019-01-15', post_id_checked='y', text_checked='y',
                             attachments_checked=None, n_attachments_checked='y', n_likes_checked=None,
                             n_reposts_checked=None, n_comments_checked=None)

    assert (b'You cannot select &#34;Number of attachments&#34; field without &#34;Attachments&#34; field'
            in response.data)


def test_no_posts_to_download(client):
    """
    check if the get_wall_posts function did not return any posts for download request
    """
    with mock.patch('app.view.get_wall_posts') as mocked_get_wall_posts:
        mocked_get_wall_posts.return_value = []
        response = download_data(client, id_='wrong_id', date='2019-01-15', post_id_checked='y', text_checked='y',
                                 attachments_checked=None, n_attachments_checked=None, n_likes_checked=None,
                                 n_reposts_checked=None, n_comments_checked=None)

        assert b'No posts for this user. Try another date or ID' in response.data


def test_no_posts_to_draw(client):
    """
    checks if the get_wall_posts function did not return any posts for draw statistics request
    """
    with mock.patch('app.view.get_wall_posts') as mocked_get_wall_posts:
        mocked_get_wall_posts.return_value = []
        response = client.post('/statistics', data=dict(
            id_='some_id', date='2019-01-01', radio='hour'), follow_redirects=True)
        assert b'No data to draw. Try another date or ID' in response.data
