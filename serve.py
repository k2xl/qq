from tornado import websocket, web, ioloop
import uuid
import json

search_map = {}
search_inverse_map = {}
give_map = {}
give_inverse_map = {}
cl = {}
room_map = {}
class SocketHandler(websocket.WebSocketHandler):
    def check_origin(self, origin):
        return True

    def poll_background(self):
      print("hi")

    def open(self):
        if self not in cl:
          cl[self] = {"username": "unknown"}
        self.send({
          "state": "init",
          "message": "you're connected to qq. cool."
          })
    def send(self, obj):
      self.write_message(
        json.dumps(obj)
        )
    def send_error(self, code, msg = "Unknown error"):
      self.send({
          "status_code": code,
          "error": msg
          })
    def register(self,target_map, target_inverse, str_tags):
      tags = str_tags.strip().split(" ")
      target_map[self] = tags
      for tag in tags:
        if tag not in target_inverse:
          target_inverse[tag] = {}
        target_inverse[tag][self] = tags

    def find_match(self, target_map, target_inverse_map):
      """
      let the givers know about my tags
      """
      my_tags = target_map[self]
      matches = []
      for my_tag in my_tags:
        if my_tag not in target_inverse_map: 
          continue
        for helper in target_inverse_map[my_tag]:
          matches.append(helper)
      return matches

    def on_message(self, msg):
      print("got ",msg)
      try:
        js = json.loads(msg)
      except Exception:
        send_error(400, "not valid json")
      
      if "type" not in js:
        return self.send_error(400, "missing type")

      if js["type"] == "subscribe":
        if "username" not in js or len(js["username"]) < 3:
          return self.send_error(401, "unauthorized user")
        if "tags" not in js or "option" not in js:
          return self.send_error(400, "tags and option are required")
        if js["option"] != "search" and js["option"] != "give":
          return self.send_error(400, "type can be search or give")

        self.username = js["username"]

        if js["option"] == "search":
          self.register(search_map, search_inverse_map, js["tags"])

          msg = "qq has you registered in system for searching for %s"%js["tags"]
          matches = self.find_match(search_map, give_inverse_map)
          for match in matches:
            match.send({
              "state": "in_chat",
              "message": "we found you a match. %s is looking for help with %s"%(self.username,search_map[self])
            })
            # race condition is probably possible if user leaves and we try to access give_map, probably need some locks?
            room_obj = [match, self]
            room_map[self] = room_obj
            room_map[match] = room_obj
            self.send({
              "state": "in_chat",
              "message": "we found you a match. %s is willing to help with %s"%(match.username,give_map[match])
            })
            self.remove_from_maps(self)
            self.remove_from_maps(match)
            break
        else:
          self.register(give_map, give_inverse_map, js["tags"])
          msg = "qq has you registered in system for offering help for %s"%js["tags"]
          matches = self.find_match(give_map, search_inverse_map)
          for match in matches:
            room_obj = [match, self]
            room_map[self] = room_obj
            room_map[match] = room_obj
            self.send({
              "state": "in_chat",
              "message": "we found you a match. %s is looking for help with %s"%(match.username,search_map[match])
            })
            # race condition is probably possible if user leaves and we try to access give_map, probably need some locks?
            match.send({
              "state": "in_chat",
              "message": "we found you a match. %s is willing to help with %s"%(self.username,give_map[self])
            })
            self.remove_from_maps(self)
            self.remove_from_maps(match)
            break

        if len(matches) == 0:
          self.send({
            "state": "wait",
            "success": True,
            "message":"%s.\nbe patient... we'll notify when we find someone matching"%msg
          })
      else:
        # Regular message?
        print("Regular message?")
        if message not in js:
          return send_error("No message found")

        if self in room_map:
          for person in room_map:
            person.send("%s says: %s"%(self.username, js["message"]))

    
      return False
    def remove_from_maps(self):
      if self in room_map:
          del room_map[self]
      if self in search_map:
        tags = search_map[self]
        del search_map[self]
      elif self in give_map:
        tags = give_map[self]
        del give_map[self]

      for tag in tags:
        if tag in search_inverse_map and self in search_inverse_map[tag]:
          del search_inverse_map[tag][self]
          if len(search_inverse_map[tag]) == 0:
            del search_inverse_map[tag]
        if tag in give_inverse_map and self in give_inverse_map[tag]:
          del give_inverse_map[tag][self]
          if len(give_inverse_map[tag]) == 0:
            del give_inverse_map[tag]
    
    def on_close(self):
        print("Someone disconnected...")
        tags = []
        self.remove_from_maps(self)
        if self in cl:
          del cl[self]
        

app = web.Application([
    (r'/ws', SocketHandler),
    (r'/(favicon.ico)', web.StaticFileHandler, {'path': '../'}),
    (r'/(rest_api_example.png)', web.StaticFileHandler, {'path': './'}),
])

if __name__ == '__main__':
    print("Starting on port 9000")
    app.listen(9000)
    ioloop.IOLoop.instance().start()