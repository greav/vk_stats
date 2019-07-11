from app import app
from flask import render_template, request, Response
from forms import DownloadForm, StatisticsForm

from matplotlib import pyplot as plt


import datetime
import calendar
import vk_api
import io
import base64
import pandas as pd
import seaborn as sns


def get_user_posts(user_id, date):
    date = datetime.datetime.strptime(date, '%Y-%m-%d')
    timestamp = calendar.timegm(date.utctimetuple())

    access_token = '94af586cbe41468638e9ba8ed84ff648cf6c90f006b2c4cbc258b7a8a13be1f7c796ebf1837ba4bdb5b7b'
    session = vk_api.VkApi(token=access_token)
    vk = session.get_api()

    post = vk.wall.get(owner_id=user_id, count=1)
    posts_count = post['count']
    valid_posts = []

    if post['items'][0]['date'] > timestamp:
        valid_posts.append(post['items'][0])

    for offset in range(1, posts_count, 100):
        posts = vk.wall.get(owner_id=user_id, count=100, offset=offset)['items']
        if posts[-1]['date'] > timestamp:
            valid_posts.extend(posts)
            continue

        for i, post in enumerate(posts):
            if post['date'] < timestamp:
                valid_posts.extend(posts[:i])
                return valid_posts

    return valid_posts


def filter_posts(posts, post_id_checked, text_checked, attachments_checked, n_attachments_checked, n_likes_checked,
                 n_reposts_checked, n_comments_checked):
    valid_posts = []
    for post in posts:
        post_id = post['id']
        text = post['text']
        attachments = post.get('attachments')
        n_attachments = len(attachments) if attachments else 0
        n_likes = post['likes']['count']
        n_comments = post['comments']['count']
        n_reposts = post['reposts']['count']

        valid_post = [post_id, '"' + text + '"', n_attachments, n_likes, n_comments, n_reposts]
        valid_posts.append(valid_post)

    return valid_posts


def filter_posts_2(posts):
    valid_posts = []
    for post in posts:
        post_id = post['id']
        date = post['date']
        n_likes = post['likes']['count']
        n_comments = post['comments']['count']
        n_reposts = post['reposts']['count']

        valid_post = [post_id, date, n_likes, n_comments, n_reposts]
        valid_posts.append(valid_post)

    return valid_posts



@app.route('/')
def index():
    return render_template('index.html')


@app.route('/download')
def download():

    form = DownloadForm()
    return render_template('download.html', form=form)


@app.route('/download/data.csv', methods=['POST'])
def generate_csv():
    user_id = int(request.form.get('user_id'))
    date = request.form.get('date')
    post_id_checked = bool(request.form.get('post_id_checked'))
    text_checked = bool(request.form.get('text_checked'))
    attachments_checked = bool(request.form.get('attachments_checked'))
    n_attachments_checked = bool(request.form.get('n_attachments_checked'))
    n_likes_checked = bool(request.form.get('n_likes_checked'))
    n_reposts_checked = bool(request.form.get('n_reposts_checked'))
    n_comments_checked = bool(request.form.get('n_comments_checked'))

    posts = get_user_posts(user_id, date)

    valid_posts = filter_posts(posts, post_id_checked, text_checked, attachments_checked, n_attachments_checked,
                               n_likes_checked, n_reposts_checked, n_comments_checked)

    def generate(posts):
        for row in posts:
            yield ','.join([str(field) for field in row]) + '\n'

    return Response(generate(valid_posts), mimetype='text/csv')


@app.route('/statistics', methods=['GET', 'POST'])
def statistics():
    form = StatisticsForm()

    if request.method == 'POST':
        user_id = int(request.form.get('user_id'))
        date = request.form.get('date')
        radio = request.form.get('radio')

        posts = get_user_posts(user_id, date)
        valid_posts = filter_posts_2(posts)

        plot_url = get_plot_url(valid_posts, radio)

        return render_template('statistics.html', form=form, figure=plot_url)

    return render_template('statistics.html', form=form, figure=None)


def get_plot_url(valid_posts, radio):
    img = io.BytesIO()

    df = pd.DataFrame(data=valid_posts, columns=['post_id', 'date', 'n_likes', 'n_comments', 'n_reposts'])
    df['date'] = pd.to_datetime(df['date'], unit='s')

    if radio == 'hour':
        gb = df.groupby(lambda i: df.loc[i, 'date'].hour)[['n_likes', 'n_comments', 'n_reposts']].agg(
            ['mean', 'count'])
        x = gb.index
    elif radio == 'dow':
        gb = df.groupby(lambda i: df.loc[i, 'date'].dayofweek)[['n_likes', 'n_comments', 'n_reposts']].agg(
            ['mean', 'count'])
        x = gb.index
    elif radio == 'month':
        gb = df.groupby(lambda i: df.loc[i, 'date'].month)[['n_likes', 'n_comments', 'n_reposts']].agg(
            ['mean', 'count'])
        x = gb.index
    elif radio == 'year':
        gb = df.groupby(lambda i: df.loc[i, 'date'].year)[['n_likes', 'n_comments', 'n_reposts']].agg(
            ['mean', 'count'])
        x = gb.index

    fig, axs = plt.subplots(nrows=2, ncols=2, figsize=(12, 8))

    sns.barplot(x, gb[('n_likes', 'count')], ax=axs[0, 0])
    sns.barplot(x, gb[('n_likes', 'mean')], ax=axs[0, 1])
    sns.barplot(x, gb[('n_comments', 'mean')], ax=axs[1, 0])
    sns.barplot(x, gb[('n_reposts', 'mean')], ax=axs[1, 1])

    axs[0, 0].set_ylabel('count')
    axs[0, 1].set_ylabel('avg')
    axs[1, 0].set_ylabel('avg')
    axs[1, 1].set_ylabel('avg')

    axs[0, 0].set_title('Number of posts')
    axs[0, 1].set_title('Average number of likes')
    axs[1, 0].set_title('Average number of comments')
    axs[1, 1].set_title('Average number of reposts')

    plt.savefig(img, format='png')
    img.seek(0)
    plot_url = base64.b64encode(img.getvalue()).decode()

    return plot_url
