VK_Stats
======

The basic app made on the Flask framework for downloading data and receiving statistics about the user's VK posts or community VK posts.

Install
-------
Clone the repository:

    $ git clone https://github.com/greav/vk_stats.git
    $ cd vk_stats

Create a virtualenv and activate it:

    $ python -m venv venv
    $ source venv/bin/activate

Install dependencies:

    $ pip install -r requirements.txt


Run
---

    $ python main.py


Open http://127.0.0.1:5000 in a browser.


Test
----

    $ python -m pytest tests/
