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
from genshi.filters import HTMLFormFiller

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
        if self.vbox.version[:3] != '2.2':
            error_message = "VBoxWeb only supports VirtualBox version 2.2.x, you are running VirtualBox %s" % (self.vbox.version,)
            tmpl = loader.load('error.html')
            return tmpl.generate(error_message=error_message).render('html', doctype='html')
        tmpl = loader.load('index.html')
        return tmpl.generate(vms=self.vbox.getMachines()).render('html', doctype='html')

    @cherrypy.expose
    def vm_info(self, uuid):
        vm = self.vbox.getMachine(uuid)
        state = VM_STATES[int(vm.state)]
        os_type_obj = self.vbox.getGuestOSType(vm.OSTypeId)
        guest_os = os_type_obj.description
        tmpl = loader.load('vm_info.html')
        return tmpl.generate(vm=vm, state=state, guest_os=guest_os).render('html', doctype='html')

    @cherrypy.expose
    def control_vm(self, uuid, action):
        if action == 'power_up':
            session = self.mgr.getSessionObject(self.vbox)
            progress = self.vbox.openRemoteSession(session, uuid, 'vrdp', '')
            progress.waitForCompletion(-1)
        else:
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

    @cherrypy.expose
    def modify_vm(self, uuid, **form_data):
        if cherrypy.request.method.upper() == 'POST':
            #TODO Some form validation might be nice, eh?
            try:
                print form_data
                session = self.mgr.getSessionObject(self.vbox)
                self.vbox.openSession(session, uuid)
                vm = session.machine
                vm.name = form_data['name']
                vm.description = form_data['description']
                vm.memorySize = form_data['memory']
                vm.VRAMSize = form_data['vram']
                if 'hwvirtex' in form_data:
                    vm.HWVirtExEnabled = 1
                else:
                    vm.HWVirtExEnabled = 0
                if 'nestedpaging' in form_data:
                    vm.HWVirtExNestedPagingEnabled = 1
                else:
                    vm.HWVirtExNestedPagingEnabled = 0
                vm.saveSettings()
                session.close()
                raise cherrypy.HTTPRedirect('/vm_info/' + uuid)
            except Exception,e:
                error_message = "Unable to modify VM. %s" % (e,)
                tmpl = loader.load('error.html')
                return tmpl.generate(error_message=error_message).render('html', doctype='html')
        else:
            vm = self.vbox.getMachine(uuid)
            form_data = {'name': vm.name,
                         'description': vm.description,
                         'memory': vm.memorySize,
                         'vram': vm.VRAMSize,
                         'hwvirtex': False,
                         'nestedpaging': vm.HWVirtExNestedPagingEnabled}
            if vm.HWVirtExEnabled == 1:
                form_data['hwvirtex'] = True
            filler = HTMLFormFiller(data=form_data)
            tmpl = loader.load('modify_vm.html')
            return tmpl.generate(vm=vm).filter(filler).render('html', doctype='html')
