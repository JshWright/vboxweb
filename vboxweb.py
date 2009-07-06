#!/usr/bin/env python
# ***** BEGIN LICENSE BLOCK *****
#
# The MIT License
#
# Copyright (c) 2009 Josh Wright
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#
# ***** END LICENSE BLOCK *****

import os, sys, pickle

USAGE = """

VBoxWeb - A web-based frontend for Sun's VirtualBox

Usage:
    -h, --help
        Print this usage list and exit
    -p, --port [port number]
        Set the port number VBoxWeb should listen on
    --vbox-path [path]
        The path to VBoxPython.so (i.e. /usr/lib/virtualbox/)        
"""

try:
    import cherrypy
    major_version = int(cherrypy.__version__[0])
    if major_version < 3:
        raise ImportError
except ImportError:
    print """
            VBoxWeb requires CherryPy (version 3.0 or higher).

            You can download the latest version of CherryPy
                    from http://www.cherrypy.org/
          """
    sys.exit()

from content import Root, VM, HardDisk

DEFAULT_SETTINGS = {'username': 'vboxweb', 'password': 'vboxweb', 'port': 8080, 'vbox_python_path': '/usr/lib/virtualbox'}

def main(argv):

    if os.path.exists('config.pkl'):
        f = open('config.pkl', 'r')
        vboxweb_config = pickle.load(f)
        f.close()
    else:
        vboxweb_config = DEFAULT_SETTINGS
        f = open('config.pkl', 'w')
        pickle.dump(vboxweb_config, f, 1)
        f.close()

    port = vboxweb_config['port']
    vbox_python_path = vboxweb_config['vbox_python_path']

    if len(argv) > 1:
        i = iter(argv)
        executable = i.next()
        for arg in i:
            if arg in ('-p', '--port'):
                port = i.next()
            elif arg == '--vbox-path':
                vbox_python_path = i.next()
            elif arg in ('-h', '--help'):
                print USAGE
                sys.exit(0)
            else:
                print "\nUnknown command: %s" % arg
                print USAGE
                sys.exit(1)

    sys.path.append(vbox_python_path)
    import xpcom.vboxxpcom
    import xpcom
    import xpcom.components
    vbox = xpcom.components.classes["@virtualbox.org/VirtualBox;1"].createInstance()

    class LocalManager:
        def getSessionObject(self, vbox):
            return xpcom.components.classes["@virtualbox.org/Session;1"].createInstance()

    cherrypy.config.update({
        'server.socket_port': port,
        'tools.encode.on': True, 'tools.encode.encoding': 'utf-8',
        'tools.decode.on': True,
        'tools.trailing_slash.on': True,
        'tools.staticdir.root': os.path.abspath(os.path.dirname(__file__)),
    })

    root = Root(LocalManager(), vbox)
    root.vm = VM(LocalManager(), vbox)
    root.hard_disk = HardDisk(LocalManager(), vbox)

    cherrypy.quickstart(root, '/', {
        '/': {
            'tools.digest_auth.on': True,
            'tools.digest_auth.realm': 'Some site',
            'tools.digest_auth.users': {vboxweb_config['username']: vboxweb_config['password']}
        },
        '/media': {
            'tools.staticdir.on': True,
            'tools.staticdir.dir': 'media'
        }
    })

if __name__ == '__main__':
    main(sys.argv)
