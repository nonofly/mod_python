 # Copyright (c) 2000 Gregory Trubetskoy.  All rights reserved.
 #
 # Redistribution and use in source and binary forms, with or without
 # modification, are permitted provided that the following conditions
 # are met:
 #
 # 1. Redistributions of source code must retain the above copyright
 #    notice, this list of conditions and the following disclaimer. 
 #
 # 2. Redistributions in binary form must reproduce the above copyright
 #    notice, this list of conditions and the following disclaimer in
 #    the documentation and/or other materials provided with the
 #    distribution.
 #
 # 3. The end-user documentation included with the redistribution, if
 #    any, must include the following acknowledgment: "This product 
 #    includes software developed by Gregory Trubetskoy."
 #    Alternately, this acknowledgment may appear in the software itself, 
 #    if and wherever such third-party acknowledgments normally appear.
 #
 # 4. The names "mod_python", "modpython" or "Gregory Trubetskoy" must not 
 #    be used to endorse or promote products derived from this software 
 #    without prior written permission. For written permission, please 
 #    contact grisha@ispol.com.
 #
 # 5. Products derived from this software may not be called "mod_python"
 #    or "modpython", nor may "mod_python" or "modpython" appear in their 
 #    names without prior written permission of Gregory Trubetskoy.
 #
 # THIS SOFTWARE IS PROVIDED BY GREGORY TRUBETSKOY ``AS IS'' AND ANY
 # EXPRESSED OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
 # IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
 # PURPOSE ARE DISCLAIMED.  IN NO EVENT SHALL GREGORY TRUBETSKOY OR
 # HIS CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
 # SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT
 # NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
 # LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
 # HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT,
 # STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
 # ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED
 # OF THE POSSIBILITY OF SUCH DAMAGE.
 # ====================================================================
 #
 # $Id: cgihandler.py,v 1.8 2000/12/05 23:47:01 gtrubetskoy Exp $

import apache
import imp
import os
import sys

# if threads are not available
# create a functionless lock object
try:
    import threading
    _lock = threading.Lock()
except (ImportError, AttributeError):
    class DummyLock:
        def acquire(self):
            pass
        def release(self):
            pass
    _lock = DummyLock()

# the next statement  deserves some explaining.
# it seems that the standard os.environ object looses
# memory if the environment is manipulated frequently. Since for
# CGI you have to rebuild it for every request, your httpd will
# grow rather fast. I am not exactly sure why it happens and if there
# is a more sensible remedy, but this seems to work OK.
os.environ = {}

original = sys.modules.keys()

# find out the standard library location
stdlib, x = os.path.split(os.__file__)

def handler(req):

    ### if you don't need indirect modules reloaded, comment out
    ### code unitl ### end

    # if there are any new modules since the import of this module,
    # delete them.
    for m in sys.modules.keys():
        if m not in original:
            # unless they are part of standard library
            mod = sys.modules[m]
            if hasattr(mod, "__file__"):
                path, x = os.path.split(mod.__file__)
                if path != stdlib:
                    del sys.modules[m]
    ### end

    # get the filename of the script
    if req.subprocess_env.has_key("script_filename"):
        dir, file = os.path.split(req.subprocess_env["script_filename"])
    else:
        dir, file = os.path.split(req.filename)
    module_name, ext = os.path.splitext(file)

    _lock.acquire()
    try:

        try:

            # The CGI spec requires us to set current working
            # directory to that of the script. This is not
            # thread safe, this is why we must obtain the lock.
            cwd = os.getcwd()
            os.chdir(dir)

            # simulate cgi environment
            env, si, so = apache.setup_cgi(req)

            try:
                # we do not search the pythonpath (security reasons)
                fd, path, desc = imp.find_module(module_name, [dir])
            except ImportError:
                raise apache.SERVER_RETURN, apache.HTTP_NOT_FOUND

            # this executes the module
            imp.load_module(module_name, fd, path, desc)

            return apache.OK

        finally:
            # unsimulate the cgi environment
            apache.restore_nocgi(env, si, so)
            try:
                fd.close()
            except: pass
            os.chdir(cwd)
    finally:
        _lock.release()

