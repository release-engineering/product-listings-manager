import tempfile
import subprocess
from textwrap import dedent
try:
    from xmlrpc.client import dumps
    from urllib.parse import urlparse
except ImportError:
    from xmlrpclib import dumps
    from urlparse import urlparse

"""
This script will benchmark getProductListings results with httperf.
"""

LABEL = 'RHEL-6-Server-EXTRAS-6'
BUILD = 'dumb-init-1.2.0-1.20170802gitd283f8a.el6'


def serialize(method, params):
    """ Return a XML-RPC representation of this method and parameters. """
    return dumps(params, method).replace("\n", '')


def run(cmd):
    """ Run a command, with logging. """
    print('+ ' + ' '.join(cmd))
    subprocess.check_call(cmd)


def get(url, sessions=100):
    """ GET a URL with httperf. """
    o = urlparse(url)
    cmd = ['httperf',
           '--hog',
           '--server', o.hostname,
           '--port', str(o.port),
           #'--add-header', 'Accept: application/json\n',
           '--uri', o.path,
           '--num-conns', str(sessions)]
    run(cmd)


def post(url, content, sessions=20):
    """ POST a URL with httperf. """
    o = urlparse(url)
    content = content.replace('"', '\\"')
    template = dedent("""
{path} method=POST contents="{content}"
""")
    config = template.format(path=o.path, content=content)
    with tempfile.NamedTemporaryFile(mode='w+') as temp:
        temp.write(config)
        temp.flush()
        wsesslog = '%s,0,%s' % (sessions, temp.name)
        cmd = ['httperf', '--hog', '--server', o.hostname, '--port', '80',
               '--method', 'POST', '--wsesslog', wsesslog]
        run(cmd)


def benchmark_xmlrpc(url):
    content = serialize('getProductListings', (LABEL, BUILD))
    post(url, content)


def benchmark_rest(url):
    template = '{base}/api/v1.0/product-listings/{label}/{build}'
    fullurl = template.format(base=url, label=LABEL, build=BUILD)
    get(fullurl)


#benchmark_xmlrpc('http://prodlistings-dev1.usersys.redhat.com/xmlrpc')
#benchmark_xmlrpc('https://brewhub.stage.engineering.redhat.com/brewhub')
#benchmark_xmlrpc('https://brewhub.engineering.redhat.com/brewhub')
#benchmark_rest('http://prodlistings-dev1.usersys.redhat.com')
benchmark_rest('http://localhost:5000')
