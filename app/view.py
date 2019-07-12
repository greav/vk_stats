from app import app
from flask import render_template, request, Response
from forms import DownloadForm, StatisticsForm
from config import ACCESS_TOKEN

from matplotlib import pyplot as plt


import datetime
import calendar
import vk_api
import io
import base64
import pandas as pd
import seaborn as sns
from collections import OrderedDict


def get_user_posts(user_id, date):
    date = datetime.datetime.strptime(date, '%Y-%m-%d')
    timestamp = calendar.timegm(date.utctimetuple())

    session = vk_api.VkApi(token=ACCESS_TOKEN)
    vk = session.get_api()

    if isinstance(user_id, int):
        kwargs = {'owner_id': user_id}
    else:
        kwargs = {'domain': user_id}

    post = vk.wall.get(**kwargs, count=1)
    posts_count = post['count']

    if posts_count == 0:
        return []

    valid_posts = []

    if post['items'][0]['date'] > timestamp:
        valid_posts.append(post['items'][0])

    for offset in range(1, posts_count, 100):
        posts = vk.wall.get(**kwargs, count=100, offset=offset)['items']
        if posts[-1]['date'] > timestamp:
            valid_posts.extend(posts)
            continue

        for i, post in enumerate(posts):
            if post['date'] < timestamp:
                valid_posts.extend(posts[:i])
                return valid_posts

    return valid_posts


@app.route('/')
def about():
    return render_template('about.html')


@app.route('/download')
def download():

    form = DownloadForm()
    return render_template('download.html', form=form)


@app.route('/download/data.csv', methods=['POST'])
def generate_csv():

    user_id = request.form.get('user_id')
    if user_id.isdigit():
        user_id = int(user_id)

    date = request.form.get('date')

    checked_fields = OrderedDict()

    checked_fields['post_id'] = bool(request.form.get('post_id_checked'))
    checked_fields['text'] = bool(request.form.get('text_checked'))
    checked_fields['attachments'] = bool(request.form.get('attachments_checked'))
    checked_fields['n_attachments'] = bool(request.form.get('n_attachments_checked'))
    checked_fields['n_likes'] = bool(request.form.get('n_likes_checked'))
    checked_fields['n_reposts'] = bool(request.form.get('n_reposts_checked'))
    checked_fields['n_comments'] = bool(request.form.get('n_comments_checked'))

    posts = get_user_posts(user_id, date)

    def generate(posts):
        header = [key for key, value in checked_fields.items() if value]
        yield ','.join(header) + '\n'
        for post in posts:
            row = []
            if checked_fields['post_id']:
                row.append(str(post['id']))
            if checked_fields['post_id']:
                text = post['text']
                row.append(f'"{text}"')
            if checked_fields['attachments']:
                attachments = get_attachments(post)
                row.append(f'"{attachments}"')
            if checked_fields['n_attachments']:
                n_attachments = len(attachments) if attachments else 0
                row.append(str(n_attachments))
            if checked_fields['n_likes']:
                row.append(str(post['likes']['count']))
            if checked_fields['n_comments']:
                row.append(str(post['comments']['count']))
            if checked_fields['n_reposts']:
                row.append(str(post['reposts']['count']))

            yield ','.join(row) + '\n'

    return Response(generate(posts), mimetype='text/csv')


def get_attachments(post):
    attachments = post.get('attachments')
    attachments_urls = []
    if attachments:
        for attachment in attachments:
            if attachment.get('type') == 'photo':
                for photocopy in attachment['photo']['sizes']:
                    if photocopy['type'] == 'x':
                        attachments_urls.append(photocopy['url'])
                        break
                continue
            if attachment.get('type') == 'link':
                attachments_urls.append(attachment['link']['url'])
                continue
            elif attachment.get('type') == 'doc':
                attachments_urls.append(attachment['doc']['url'])
                continue
            elif attachment.get('type') == 'video':
                video_id = attachment['video']['id']
                owner_id = attachment['video']['owner_id']
                video_url = f'https://vk.com/video{owner_id}_{video_id}'
                attachments_urls.append(video_url)
    elif post.get('copy_history'):
        repost = post['copy_history'][0]
        post_id = repost['id']
        owner_id = repost['owner_id']
        repost_url = f'https://vk.com/wall{owner_id}_{post_id}'
        attachments_urls.append(repost_url)

    return attachments_urls


@app.route('/statistics', methods=['GET', 'POST'])
def statistics():
    form = StatisticsForm()

    if request.method == 'POST':
        user_id = int(request.form.get('user_id'))
        date = request.form.get('date')
        radio = request.form.get('radio')

        posts = filter_posts(get_user_posts(user_id, date))
        plot_url = get_plot_url(posts, radio)

        return render_template('statistics.html', form=form, figure=plot_url)

    return render_template('statistics.html', form=form, figure=None)


def filter_posts(posts):
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
