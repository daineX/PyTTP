# -*- coding: utf-8 -*-
from wsgiref.simple_server import make_server
from subprocess import Popen, call, PIPE
import os
from basic_auth import HTTPBasic
from timeout import *
import datetime

hltv_directory = "/home/hltv/hlds"
hltv_executable = os.path.join(hltv_directory, "hltv")
cstrike_directory = os.path.join(hltv_directory, "cstrike")

demo_download_directory = "/var/www/demos"

remote_name="voynich.homelinux.net"
remote_http="http://voynich.homelinux.net"
remote_demos=os.path.join(remote_http, "demos")

alin_ip = "78.143.41.199"
alin_port = "27015"
alin_pw = "teamnoa"

Header = """ <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"
        "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" lang="en" xml:lang="en">
    <head>
        <meta http-equiv="Content-Type" content="text/html;charset=utf-8" />
        <title>HLTV Webinterface</title>
        <style type="text/css">
            body 
            {
                font-family:Helvetica,Arial,sans-serif;
            }
            .formdiv
            {
                font-size: 10pt;
            }
        </style>
    </head>
    <body><div>"""

Body = """</div>
        <h1>HLTV</h1>
            <h2>Status</h2>
                <div>{status}</div>
            <h2>Start/Stop</h2>
                <form action=".">
                    <div class="formdiv">
                        <table>
                            <tr>
                                <td>
                                    IP:Port
                                </td>
                                <td>
                                    <input type="text" size="25" name="ip" value="{alin_ip}:{alin_port}"/>
                                </td>
                            </tr>
                            <tr>
                                <td>
                                    Passwort 
                                </td>
                                <td>
                                    <input type="password" size="25" value="{alin_pw}" name="pass"/>
                                </td>
                            </tr>
                            <tr>
                                <td>
                                    Demos aufnehmen
                                </td>
                                <td>
                                    <input type="checkbox" name="demos" value="on"/>
                                </td>
                            </tr>
                            <tr>
                                <td>
                                    Demoname
                                </td>
                                <td>
                                    <input type="text" size="25" name="demoname" value="demo"/><br/>
                                </td>
                            </tr>
                            <tr>
                                <td>
                                    <input type="submit" name="action" value ="Start"/>
                                </td>
                                <td>
                                    <input type="submit" name="action" value ="Stop"/>
                                </td>
                            </tr>
                        </table>
                    </div>
                </form>   
            <h2>Demos</h2>
                <form action=".">
                    <div class="formdiv">
                        <input type="hidden"/>
                        <select name="demo_indices" size="7" multiple="multiple">
                            {demo_options}
                        </select><br/>
                        <input type="submit" value="Zippen" name="action"/><input type="submit" value="Loeschen" name="action"/>
                    </div>
                </form>"""

Footer = """
<p>
    <a href="http://validator.w3.org/check?uri=referer"><img
        src="http://www.w3.org/Icons/valid-xhtml10"
        alt="Valid XHTML 1.0 Strict" height="31" width="88" /></a>
  </p>

    </body>
</html>
"""


class Webinterface (object):



    def __init__(self):
        self.hltv_proc = None

    def isRunning(self):
        return not call(["pidof", "hltv"])


    def stop_hltv(self):
        if self.hltv_proc:
            try:
                timeout_comm = TimeoutFunction(self.hltv_proc.communicate, 20)
                timeout_comm("quit\n")
                self.hltv_proc = None
            except TimeoutFunctionException:
                print "Timeout exceeded!"
                self.kill_hltv()


    def kill_hltv(self):
        self.hltv_proc.kill()

    def start_hltv(self, ip, password, demos, demoname):
        if self.isRunning():
            return 0
        os.chdir(hltv_directory)
        if not demos:
            self.hltv_proc = Popen([hltv_executable, "+serverpassword", password, "+connect", "%s" % (ip)], stdin=PIPE, env={'LD_LIBRARY_PATH': hltv_directory})
            return self.hltv_proc.pid
        else:
            self.hltv_proc = Popen([hltv_executable, "+serverpassword", password, "+connect", "%s" % (ip), "+record", demoname], stdin= PIPE, env={'LD_LIBRARY_PATH': hltv_directory})
            return self.hltv_proc.pid


    def get_status(self):
        return ["Not Running", "Running"][self.isRunning()]


    def parse_query_string(self, query_string):
        entries = [entry.split("=") for entry in query_string.split("&")]
        dictionary = dict()
        for entry in [entry_ for entry_ in entries if len(entry_) == 2]:
            if entry[0] in dictionary:
                if isinstance(dictionary[entry[0]], list):
                    dictionary[entry[0]].append(entry[1])
                else:
                    dictionary[entry[0]] = [dictionary[entry[0]], entry[1]]
            else:
                dictionary[entry[0]] = entry[1]
        return dictionary


    def get_demos(self, directory):
        if not os.path.isdir(directory):
            return []
        return sorted(f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory,f)) and f.endswith(".dem"))


    def zip_demos(self, demos, selection):
        filelist = []
        for index, file in enumerate(demos):
            if str(index) in selection:
                filelist.append(file)
        zip_name = datetime.datetime.now().isoformat().replace(":","-") + ".zip"
        os.chdir(cstrike_directory)
        if call(["zip", zip_name] + filelist):
            return "Zipping failed!"
        if call(["mv", zip_name, demo_download_directory]):
            return "Moving failed!"
        return zip_name


    def del_demos(self, demos, selection):
        filelist = []
        for index, file in enumerate(demos):
            if str(index) in selection:
                filelist.append(file)
        if call(["rm"] + filelist):
            return "Failed!"
        return "Done!"


    def serve(self, environ, start_response):
        try:
            if not environ.has_key('REMOTE_USER'):
                status = '401 Unauthorized'
                headers = [('Content-type', 'text/html'), ('WWW-Authenticate', 'Basic realm="Hello"')]
                start_response(status, headers)
            else:
                status = "200 OK"
                headers = [('Content-type', 'text/html')]
                start_response(status, headers)

                yield Header
                parameters =  self.parse_query_string(environ['QUERY_STRING'])
                if parameters.has_key('action'):
                    if parameters['action'] == 'Stop':
                        self.stop_hltv()
                    elif parameters['action'] == 'kill':
                        self.kill_hltv()
                    elif parameters['action'] == 'Start':
                        if not parameters.has_key('ip') or not parameters.has_key('pass'):
                            yield "Parameter missing"
                        else:
                            demos = False
                            if parameters.has_key('demos'):
                                demos = True
                            pid = self.start_hltv(parameters['ip'], parameters['pass'], demos, parameters['demoname'])
                            if pid:
                                yield "Started HLTV; Process ID: %s" % pid
                            else:
                                yield "Already started."
                    elif parameters['action'] == 'Zippen':
                        if parameters.has_key('demo_indices'):
                            demo_zip = parameters['demo_indices']
                            if isinstance(demo_zip, str):
                                demo_zip = [demo_zip]
                            yield "Zipping %s demo%s... " % (len(demo_zip), ["", "s"][len(demo_zip) > 1])
                            demos = self.get_demos(cstrike_directory)
                            zip_filename = self.zip_demos(demos, demo_zip)
                            if not zip_filename.endswith(".zip"):
                                yield "Failure: %s" % zip_filename
                            else:
                                yield 'Done!<br/ ><a href="%s">%s</a><br/ >' % (os.path.join(remote_demos, zip_filename), zip_filename)
                    elif parameters['action'] == 'Loeschen':
                        print "Loeschen"
                        if parameters.has_key('demo_indices'):
                            demo_del = parameters['demo_indices']
                            if isinstance(demo_del, str):
                                demo_del = [demo_del]
                            yield "Deleting %s demo%s... " % (len(demo_del), ["", "s"][len(demo_del) > 1])
                            demos = [os.path.join(cstrike_directory, f) for f in self.get_demos(cstrike_directory)]
                            yield "Result: %s<br/ >" % del_demos(demos, demo_del)

                template_values = {}
                template_values['status'] = self.get_status()
                template_values['demo_options'] = ('\n'+7*4*' ').join('<option value="%s">%s</option>' % (index, file) for index, file in enumerate(self.get_demos(cstrike_directory)))
                template_values['alin_ip'] = alin_ip
                template_values['alin_port'] = alin_port
                template_values['alin_pw'] = alin_pw
                yield Body.format(**template_values)
                yield Footer
        except Exception, e:
            print e
            yield str(e)

if __name__ == "__main__":
    web = Webinterface()

    import sys
    from network import AppHandler, HTTPListener, ParallelSocketListener
    port = int(sys.argv[1])
    handler = AppHandler(HTTPBasic(web.serve, {"alin": "teamnoa"}, "HLTV"), port)

#    handler = AppHandler(web.serve, port)
#    http = HTTPListener(port = port, handler = handler)   
    http = ParallelSocketListener(port = port, handler = handler)

    try:
        http.serve()
    except KeyboardInterrupt:
        http.socket.close()

#    httpd = make_server('', 61450, HTTPBasic(web.serve, {"alin": "teamnoa"}, "HLTV"))
#    httpd.serve_forever()

