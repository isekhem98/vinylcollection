import os

token = os.environ['GIST_TOKEN']
html = open('index.html').read()
html = html.replace('%%GIST_TOKEN%%', token)
open('_site/index.html', 'w').write(html)
