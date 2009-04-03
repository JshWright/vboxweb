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

import os, sys, traceback, cherrypy
from genshi.template import TemplateLoader

sys.path.append('/usr/lib/virtualbox')

import xpcom.vboxxpcom
import xpcom
import xpcom.components

loader = TemplateLoader(
    os.path.join(os.path.dirname(__file__), 'templates'),
    auto_reload=True
)

VM_STATES = (None, 'Powered Off', 'Saved', 'Aborted', 'Running', 'Paused',
                'Stuck', 'Starting', 'Stopping', 'Saving', 'Restoring',
                'Discarding', 'Setting Up')

class Root:

    def __init__(self):

        class LocalManager:
            def getSessionObject(self, vbox):
                return xpcom.components.classes["@virtualbox.org/Session;1"].createInstance()

        self.mgr = LocalManager()
        self.vbox = xpcom.components.classes["@virtualbox.org/VirtualBox;1"].createInstance()

    def get_existing_session(self, uuid):
        session = self.mgr.getSessionObject(self.vbox)
        try:
            self.vbox.openExistingSession(session, uuid)
        except Exception,e:
            return "Unable to process action: %s" % e
        return session

    @cherrypy.expose
    def index(self):
        tmpl = loader.load('index.html')
        return tmpl.generate(vms=self.vbox.getMachines()).render('html', doctype='html')

    @cherrypy.expose
    def vm_info(self, uuid):
        vm = self.vbox.getMachine(uuid)
        state = VM_STATES[int(vm.state)]
        tmpl = loader.load('vm_info.html')
        return tmpl.generate(vm=vm, state=state).render('html', doctype='html')

    @cherrypy.expose
    def control_vm(self, uuid, action):
        session = self.get_existing_session(uuid)
        console = session.console
        if action == 'power_off':
            console.powerDown()
        elif action == 'pause':
            console.pause()
        elif action == 'resume':
            console.resume()
        session.close()
        raise cherrypy.HTTPRedirect('/vm_info/' + uuid) 
