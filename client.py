from ws4py.client.threadedclient import WebSocketClient
from ws4py import format_addresses, configure_logger
import json
import time
import thread
import argparse

logger = configure_logger()
parser = argparse.ArgumentParser(description='client for qq')
parser.add_argument('-host', action="store", dest="host", default="localhost")
parser.add_argument('-port', action="store", dest="port", default=9000)
parser.add_argument('-username', action="store", dest="username")
parser.add_argument('-give', action="store", dest="give")
parser.add_argument('-search', action="store", dest="search")
args = parser.parse_args()
class DummyClient(WebSocketClient):
    def opened(self):
        logger.info("cool.")
        self.is_connected = True
        self.state = "wait"
        thread.start_new_thread(self.state_machine, ())
    def cls(self):
        print(chr(27) + "[2J")

    def state_machine(self):
        global args
        while self.is_connected:
            if self.state == "init":
                username = args.username
                while username == None or len(username) < 1:
                    username = raw_input("username:")

                options = ["search", "give"]
                tags = ""
                if "give" in args:
                    option_s = "2"
                    tags = args.give
                elif "search" in options:
                    option_s = "1"
                    tags = args.search

                while option_s != "1" and option_s != "2": 
                    option_s = (raw_input("\nwelcome to qq %s. are you \n1) searching for help?\n2) offering help?\n3) what is qq?\n4) who's available?\n"%username))
                option = int(option_s)-1
                print("YOUR OPTION WAS %s"%options[option])
                
                while len(tags) < 1:
                    tags = raw_input("enter hashtags (space separated) keywords. example would be redis tornado linux)\n")

                send_obj = {
                    "type": "subscribe",
                    "username": username,
                    "option": options[option],
                    "tags": tags
                }
                self.send(json.dumps(send_obj))
                print("sent...")
                self.state = "wait"
            else:
                # we should be in waiting state
                if self.state != "wait":
                    print("error: we are in a strange state issued from server the client doesn't know how to deal with. the state is %s"%self.state)
                    self.close(reason='weird state')
                time.sleep(0.5)


    def closed(self, code, reason=None):
        self.is_connected = False
        print("Closed down", code, reason)

    def received_message(self, rec):
        m = json.loads(str(rec))
        if "error" in m:
            if "status_code" not in m:
                m["status_code"] = -1
            print("got error (status %d): %s\n"%(m["status_code"], m["error"]))
            self.close(reason='bye bye')
        elif "message" in m:
            print(m["message"])
        #if len(m) == 175:
        #    self.close(reason='Bye bye')
        if "state" in m:
            self.state = m["state"]

if __name__ == '__main__':
    try:
        ws = DummyClient("ws://%s:%s/ws"%(args.host,args.port), protocols=['http-only', 'chat'])
        ws.connect()
        ws.run_forever()
    except KeyboardInterrupt:
        ws.close()