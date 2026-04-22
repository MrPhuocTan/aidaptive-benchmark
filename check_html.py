from html.parser import HTMLParser

class MyHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []
        self.void_elements = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'}

    def handle_starttag(self, tag, attrs):
        if tag not in self.void_elements:
            self.tags.append((tag, self.getpos()))

    def handle_endtag(self, tag):
        if tag in self.void_elements:
            return
        if not self.tags:
            print(f"Error: Unexpected closing tag </{tag}> at line {self.getpos()[0]}")
            return
        last_tag, pos = self.tags.pop()
        if last_tag != tag:
            print(f"Error: Mismatched tags. Expected </{last_tag}> (opened at line {pos[0]}), got </{tag}> at line {self.getpos()[0]}")
            # Try to recover by popping until we find the matching tag
            while self.tags and self.tags[-1][0] != tag:
                self.tags.pop()
            if self.tags:
                self.tags.pop()

    def check_file(self, content):
        self.feed(content)
        if self.tags:
            print(f"Error: Unclosed tags remaining: {[t[0] for t in self.tags]}")

import os
for f in os.listdir('templates'):
    if f.endswith('.html'):
        print(f"Checking {f}...")
        parser = MyHTMLParser()
        with open(os.path.join('templates', f)) as fp:
            parser.check_file(fp.read())
