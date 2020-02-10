import socket
import multiprocessing
import pickle
import random
import string

HOST = str(socket.gethostbyname(socket.gethostname()))
PORT = 8000

room_meta={"test":{"room_name":"cosy af","current_song":["spotify:track:3Zigq1lfHmFRlyoRrh9k2s"],"progress": "44000","users":[],"is_playing":True}}
room_process_list={"null":{"queue":"queue"}}


def init():
    print("Getting ip...")
    ip_check = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    ip_check.connect(("8.8.8.8", 80))
    HOST = ip_check.getsockname()[0]
    ip_check.close()
    s = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    s.bind((HOST,PORT))
    main(s)
    print("listening on port "+str(PORT)+" under address "+str(HOST))

def main(s):
    while True:
        s.listen()
        conn,addr = s.accept()
        print("Conn established to "+str(addr))
        room_value = ""
        data = b""
        while True:
            print("receiving")
            datachunk=conn.recv(1024)
            data += datachunk
            print(len(datachunk))
            if (not datachunk) and data != b"":
                initial_request = pickle.loads(data)
                print("breaking loop")
                print(initial_request)
                break
            elif len(datachunk)<1024:
                initial_request = pickle.loads(data)
                print(initial_request)
                break
        print("passed loop")
        if initial_request["command"] == "join":
            print("room_id"+str(initial_request["id"]))
            if initial_request["id"] in room_meta:
                room_meta[initial_request["id"]] = get_timestamp(conn,id)
                room_meta[str(initial_request["id"])]["users"].append(initial_request["name"])
                room_process_list[str(initial_request["id"])]["conn"].append(conn)
                room_value=room_meta[str(initial_request["id"])]
            else:
                room_value={"state":"invalid"}
            conn.sendall(pickle.dumps(room_value))
            if room_value["state"] != "invalid":
                queue_to_use = room_process_list[str(initial_request["id"])]["queue"]
                user_listener = multiprocessing.Process(target=listener,args=(queue_to_use,conn))
                user_listener.start()
        elif initial_request["command"]== "create":
            print("creating room")
            new_room_id = create_room(conn,initial_request["room_meta"]["room_name"],initial_request["room_meta"])
            queue_to_use = room_process_list[str(new_room_id)]["queue"]
            user_listener = multiprocessing.Process(target=listener,args=(queue_to_use,conn))
            user_listener.start()


def get_timestamp(conn,id):
    room_meta["users"][0].send(pickle.dumps({"command":"timestamp"}))
    returned_time = b""
    while True:
        datachunk = room_meta["users"][0].recv(1024)
        returned_time+=datachunk
        if not datachunk and returned_time != b"":
            break
        elif len(datachunk)<1024:
            break
    conn.send(pickle.dumps({"command":"playback-pos","item":returned_time}))
    return returned_time["timestamp"]

def create_room(conn,room_name,meta):
    letters = string.ascii_letters + string.digits
    while True:
        id = ''.join(random.choice(letters) for i in range(8))
        if id not in room_meta:
            break
    print("room id: "+str(id))
    conn.send(pickle.dumps({"id":str(id)}))
    print(meta)
    room_meta[str(id)] = meta
    q = multiprocessing.Queue()
    room_main_process = multiprocessing.Process(target=room_handler,args=(q,id))
    room_process_list[str(id)]= {"queue":q,"conn":[conn]}
    room_main_process.start()
    return id

def listener(q,conn):
    data=""
    while True:
        datachunk = conn.recv(20).encode("utf-8")
        if datachunk:
            data+=str(datachunk)
            while True:
                datachunk=conn.recv(20).encode("utf-8")
                data+=datachunk
                if not datachunk and data != "":
                    q.put(data)
                    print(q.get())
                    data = ""
                    break

class room_handler():
    def __init__(self,q,room_id):
        self.specific_room_meta = room_meta[str(room_id)]
        print(room_meta)
        self.users =  room_meta[str(room_id)]["users"]
        self.conn_list = room_process_list[str(room_id)]["conn"]
        while True:
            try:
                datachunk = q.get()[0]
            except:
                datachunk=None
            if datachunk is not None:
                check_for_change(users)
            else:
                handler(datachunk)
            if (len(self.users))==0:
                del room_meta[str(room_id)]
                del room_process_list[str(room_id)]
                break

    def check_for_user_change(users,room_id):    #function checks if user left or joined
        diff = len(users)-len(room_meta[str(room_id)]["users"])
        if diff == 0:
            pass
        elif diff<0:
            for i in range(1,len(users),1):
                if users[i] not in room_meta[str(room_id)]["users"]:
                    changed_user = self.users[i]
                    self.conn_list.remove(i)
                    room_process_list[str(room_id)]["conn"] =  self.conn_list
                    self.users = room_meta[room_id]["users"]
                    for g in range(0,len(self.conn_list),1):
                        self.conn_list[g].send(pickle.dumps({"command":"usr-leave","item":str(changed_user)}))
        elif diff>0:
            self.users = room_meta[str(room_id)]["users"]
            self.specific_room_meta["users"] = self.users
            for g in range(0,len(self.conn_list),1):
                g.send(pickle.dumps({"command":"usr-join","item":str(users[len(users)-1])}))
            self.conn_list = room_process_list[str(room_id)]["conn"]
        return


    def handler(data):
        valid_requests = ["rm","add","play","pause","playback-pos"]
        request = pickle.loads(data)
        if request["command"] in valid_requests:
            for g in range(0,len(self.conn_list),1):
                self.conn_list[g].send(pickle.dumps(data))
        else:
            print("invalid request:"+str(request))



if __name__=="__main__":
    init()
