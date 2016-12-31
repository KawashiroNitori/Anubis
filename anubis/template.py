import hashlib
import misaka
from os import path
from urllib import parse

import jinja2
import jinja2.ext
import jinja2.runtime
import markupsafe

import anubis
from anubis.util import json
from anubis.util import options


class Undefined(jinja2.runtime.Undefined):

    def __getitem__(self, item):
        return self


class Environment(jinja2.Environment):

    def __init__(self):
        super(Environment, self).__init__(
            loader=jinja2.FileSystemLoader(path.join(path.dirname(__file__), 'ui/templates')),
            extensions=[jinja2.ext.with_],
            auto_reload=options.options.debug,
            autoescape=True,
            trim_blocks=True,
            undefined=Undefined
        )
        globals()[self.__class__.__name__] = lambda: self

        self.globals['anubis'] = anubis
        self.globals['static_url'] = lambda s: options.options.cdn_prefix + s
        self.globals['paginate'] = paginate

        self.filters['markdown'] = markdown
        self.filters['json'] = json.encode
        self.filters['gravatar'] = gravatar_url


MARKDOWN_EXTENSIONS = (
    misaka.EXT_TABLES |                # Parse PHP-Markdown style tables.
    misaka.EXT_FENCED_CODE |           # Parse fenced code blocks.
    misaka.EXT_AUTOLINK |              # Automatically turn safe URLs into links.
    misaka.EXT_NO_INTRA_EMPHASIS |     # Disable emphasis_between_words.
    misaka.EXT_MATH |                  # Parse TeX $$math$$ syntax.
    misaka.EXT_MATH_EXPLICIT           # Instead of guessing by context.
)

MARKDOWN_RENDER_FLAGS = (
    misaka.HTML_ESCAPE |               # Escape all HTML.
    misaka.HTML_HARD_WRAP              # Render each linebreak as <br>.
)


def markdown(text):
    return markupsafe.Markup(
        misaka.html(text, extensions=MARKDOWN_EXTENSIONS, render_flags=MARKDOWN_RENDER_FLAGS)
    )


def gravatar_url(gravatar, size=200):
    # TODO: 'd' should be http://domain/img/avatar.png
    if gravatar:
        gravatar_hash = hashlib.md5(gravatar.lower().encode()).hexdigest()
    else:
        gravatar_hash = ''
    return ('//gravatar.proxy.ustclug.org/avatar/' + gravatar_hash + '?' +
            parse.urlencode({'d': 'mm', 's': str(size)}))


def paginate(page, num_pages):
    radius = 2
    if page > 1:
        yield 'first', 1
        yield 'previous', page - 1
    if page <= radius:
        first, last = 1, min(1, radius * 2, num_pages)
    elif page >= num_pages - radius:
        first, last = max(1, num_pages - radius * 2), num_pages
    else:
        first, last = page - radius, page + radius
    if first > 1:
        yield 'ellipsis', 0
    for page0 in range(first, last + 1):
        if page0 != page:
            yield 'page', page0
        else:
            yield 'current', page
    if last < num_pages:
        yield 'ellipsis', 0
    if page < num_pages:
        yield 'next', page + 1
        yield 'last', num_pages
