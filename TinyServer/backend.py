from functools import wraps
from datetime import datetime
import os
import pathlib
import socket
import sys

import zipstream
from bottle import Bottle, HTTPError, redirect, request, response, route, run, static_file
from kivy.config import ConfigParser

app = Bottle()


def load_config():
    global root, allow_uploads, port
    config = ConfigParser()
    config.read('serverconfig.ini')
    config.setdefaults('main', {
        'root': '/sdcard',
        'allow_uploads': False,
        'port': 11451
    })
    root = pathlib.Path(config['main']['root'])
    allow_uploads = config.getboolean('main', 'allow_uploads')
    port = config.getint('main', 'port')


load_config()


def removebase(root, path) -> pathlib.Path:
    return pathlib.Path(*pathlib.Path(path).parts[len(pathlib.Path(root).parts):])


def gencontent(base, folder):
    for current, subfolders, files in os.walk(folder):
        current = pathlib.Path(current)
        yield '<ul>'
        for subfolder in subfolders:
            subfolder = current / subfolder
            link = ('zip' / removebase(base, subfolder)).as_posix() + '.zip'
            yield f'<li><details><summary>{subfolder.name} (<a href="{link}">zip</a>)</summary><form action="/upload/{removebase(base, subfolder).as_posix()}" method="post" enctype="multipart/form-data"><input type="file" name="upload" /><input type="submit" value="upload" /></form>'
            sub = gencontent(base, subfolder)
            for subcontent in sub:
                yield subcontent
            yield '</details></li>'
        for f in files:
            f = current / f
            link1 = ('static' / removebase(base, f)).as_posix()
            link2 = ('view' / removebase(base, f)).as_posix()
            yield f'<li>{f.name} (<a href="{link1}">download</a>) (<a href="{link2}">view</a>)</li>'
        yield '</ul>'
        break


def genzip(base):
    with zipstream.ZipFile(allowZip64=True) as z:
        for folder, subfolders, files in os.walk(base):
            folder = pathlib.Path(folder)
            if folder == base:
                for f in files:
                    z.write(folder / f, f)
            else:
                z.write(folder, removebase(base, folder))
                for f in files:
                    z.write(folder / f, removebase(base, folder / f))
        for data in z:
            yield data


@app.route('/')
def index():
    def generator():
        global root
        yield f'<!DOCTYPE html><html><head><title>{root.name}</title></head><body><h1>{root.name} (<a href="/{root.name}.zip">zip</a>)</h1>'
        yield '<form action="/upload" method="post" enctype="multipart/form-data"><input type="file" name="upload" /><input type="submit" value="upload" /></form>'
        for content in gencontent(root, root):
            yield content
        yield '</body></html>'
    return generator()


@route(f'/{root.name}.zip')
def send_root_zip():
    global root
    response.content_type = 'application/zip'
    return genzip(root)


@app.route('/static/<name:path>')
def send_static(name):
    return static_file(name, root=root, download=name)


@app.route('/view/<name:path>')
def view(name):
    return static_file(name, root=root)


@app.route('/zip/<name:path>')
def send_zip(name):
    name = root / name.removesuffix('.zip')
    response.content_type = 'application/zip'
    return genzip(name)


@app.route('/upload', method='POST')
def upload_to_root():
    global allow_uploads
    print(allow_uploads)
    if allow_uploads:
        upload = request.files.get('upload')
        if upload:
            upload.save(root.as_posix())
        redirect('/')
    else:
        raise HTTPError(403, 'upload not permitted')


@app.route('/upload/<name:path>', method='POST')
def do_upload(name):
    global allow_uploads
    if allow_uploads:
        upload = request.files.get('upload')
        if upload:
            upload.save(name)
        redirect('/')
    else:
        raise HTTPError(403, 'upload not permitted')


def main():
    global port
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        ip = s.getsockname()[0]
    except:
        ip = '127.0.0.1'
    finally:
        s.close()
    run(app, host=ip, port=port)
