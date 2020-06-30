import socket
import multiprocessing
import pickle
import random
import string
import sys
import time

HOST = str(socket.gethostbyname(socket.gethostname()))
PORT = 8000

room_meta={"test":{"room_name":"cosy af","current_song":["spotify:track:3Zigq1lfHmFRlyoRrh9k2s"],"progress": "44000","users":[],"is_playing":True}}
room_process_list={"null":{"queue":"queue"}}

user_listener = []
room_main = []

def init():
    print("Getting ip...")
    ip_check = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    ip_check.connect(("8.8.8.8", 80))
    HOST = ip_check.getsockname()[0]
    ip_check.close()
    s = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    s.bind((HOST,PORT))
    print("listening on port "+str(PORT)+" under address "+str(HOST))
    main(s)


def main(s):
    while True:
        s.listen()
        conn,addr = s.accept()
        print("Conn established to "+str(addr))
        room_value = ""
        data = b""
        count = 0
        while True:
            if count == 100:
                print("error occured")
                initial_request = {"command":"error"}
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
            count+=1
        count = 0
        print("passed loop")
        if initial_request["command"] == "join":
            print("room_id "+str(initial_request["id"]))
            if initial_request["id"] in room_meta:
                room_meta[initial_request["id"]]["progress"],room_meta[initial_request["id"]]["current_song"] = get_timestamp(conn,initial_request["id"])
                #room_meta[initial_request["id"]]["progress"] = "00000"
                room_meta[str(initial_request["id"])]["users"].append(initial_request["name"])               
                count = 0
                room_data = {}
                while True:                                   
                    try:
                        print(room_process_list[str(initial_request["id"])]["process_queue"])
                        room_data=room_process_list[str(initial_request["id"])]["process_queue"].get_nowait()
                    except:
                        if count==60:
                            send_error(conn)
                            break
                        time.sleep(1)
                        count+=1
                    try:
                        print(room_data)
                        if room_data["kind"]=="update_meta":
                            usable = True
                        else:
                            usable = False
                    except:
                        usable = False
                    if usable and room_data:
                        print(room_data)
                        room_value = room_data["meta"]
                        room_value["users"].append(initial_request["name"])
                        room_process_list[str(initial_request["id"])]["process_queue"].put({"kind":"update_meta","meta":room_value})
                        break
                    else:                        
                        if room_data:
                            room_process_list[str(initial_request["id"])]["process_queue"].put(room_data)                      
                room_value["is_playing"]=True
                room_value["state"]="valid"
                print(room_value)
            else:
                room_value={"state":"invalid"}
            conn.sendall(pickle.dumps(room_value))
            if room_value["state"] == "valid":
                print("joining...")
                conn_list = room_process_list[str(initial_request["id"])]["conn"]
                print(conn_list)
                conn_list.append(conn)
                room_process_list[str(initial_request["id"])]["conn"] = conn_list
                room_process_list[initial_request["id"]]["process_queue"].put({"kind":"conn_list","payload":conn_list})
                queue_to_use = room_process_list[str(initial_request["id"])]["queue"]
                user_listener.append(multiprocessing.Process(target=listener,args=(queue_to_use,conn)))
                queue_to_use.put(pickle.dumps({"command":"usr-join","item":initial_request["name"]}))
                print("starting listener")
                user_listener[len(user_listener)-1].start()
        elif initial_request["command"]== "create":
            print("creating room")
            new_room_id = create_room(conn,initial_request["room_meta"]["room_name"],initial_request["room_meta"])
            queue_to_use = room_process_list[str(new_room_id)]["queue"]
            room_process_queue = room_process_list[str(new_room_id)]["process_queue"]
            user_listener.append( multiprocessing.Process(target=listener,args=(queue_to_use,conn)))
            room_main.append(multiprocessing.Process(target=room_handler,args=(queue_to_use,new_room_id,room_process_queue)))
            try:
                user_listener[len(user_listener)-1].start()
            except  Exception as e:
                print(e)
                sys.exit()
            room_main[len(room_main)-1].start()
            
def send_error(conn):
    print("error with new connection")
    

def get_timestamp(conn,id):
    print(id)
    client_conn = room_process_list[str(id)]["conn"][0]
    print(client_conn)
    client_conn.send(pickle.dumps({"command":"timestamp"}))
    count = 0
    while True:
        try:
            queue_data = room_process_list[id]["process_queue"].get_nowait()
            print(queue_data)
            if queue_data["kind"] == "timestamp":
                print("timestamp found")
                time_to_send = queue_data["time"]
                current_song = queue_data["current_song"]
                break
            elif queue_data["kind"]!="timestamp":
                room_process_list[id]["process_queue"].put(queue_data)
        except:
            count += 1
            room_process_list[str(id)]["conn"][1].send(pickle.dumps({"command":"timestamp"}))
            if count == 50:
                send_error(conn)
                return 0
            time.sleep(0.5)
    return time_to_send,current_song
    
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
    pq = multiprocessing.Queue()
    room_process_list[str(id)]= {"queue":q,"conn":[conn],"process_queue":pq}
    return id

def listener(q,conn):
    data=b""
    print("listener:"+str(conn))
    count = 0
    while True:
        if count == 100:
            conn.sendall(pickle.dumps({"command":"alive"}))
            data = conn.recv(20)
            if data and data!=b"":
                count = 0
            else:
                conn.close()
                return        
        print("listening")
        try:
            datachunk=conn.recv(20)
        except:
            if datachunk:
                if len(datachunk)<20:
                    pass
                elif len(datachunk)==0:
                    break
            count +=1
        print(len(datachunk))
        data+=datachunk
        #print(data)
        print("test")
        if len(datachunk)<20 and data != b"":
            q.put(data)
            print("data in queue")
            #q.task_done()
            command = pickle.loads(data)["command"]
            print(command)
            if command == "usr-leave":
                conn.close()
                return
            data = b""
        elif data==b"":
            count +=1
            
                

class room_handler():
    def __init__(self,q,room_id,room_q):
        self.r_id = room_id
        self.specific_room_meta = room_meta[str(room_id)]
        print(room_meta)
        self.users =  room_meta[str(room_id)]["users"]
        print(self.users)
        self.conn_list = room_process_list[str(room_id)]["conn"]
        self.room_q = room_q
        while True:
            self.room_meta_update(room_q)
            room_q.put({"kind":"update_meta","meta":self.specific_room_meta})
            datachunk=None
            try:
                datachunk = q.get_nowait()
                print("recvd")
            except  Exception as e:
                try:
                    print("exception"+e)
                except:
                    pass
            if datachunk is not None:
                print("handling data")
                self.handler(datachunk)
            if (len(self.specific_room_meta["users"]))==0:
                print("deleting room: "+str(room_id))
                del room_meta[str(room_id)]
                del room_process_list[str(room_id)]
                return
                #should end process and therefore no longer accept connections to abandoned room
            #print("reached end of loop")
                
    def room_meta_update(self,q,previous_data=None):
        try:
            data = q.get_nowait()
        except:
            return
        if data:
            if data["kind"]=="room_meta":
                self.specific_room_meta=data["payload"]
            elif data["kind"]=="conn_list":
                self.conn_list = data["payload"]
            elif data["kind"]=="update_meta":
                if data != previous_data:
                    self.room_meta_update(q,data)
                if len(data["meta"]["users"])!=len(self.specific_room_meta["users"]):
                    x = []
                    x.append(data["meta"]["users"])
                    print(x)
                    self.users_changed(x)
                    self.specific_room_meta["users"]=data["meta"]["users"]
            elif data["kind"]=="timestamp":
                q.put(data)   
            else:
                print("unexpected input for room_handler.room_meta_update:"+str(data))            
        return
       
    def users_changed(self,new_user_list):
        if len(new_user_list)==0:
            return
        diff = len(new_user_list)-len(self.users)
        print("new users:"+str(new_user_list))
        print("self.users"+str(self.users))
        print("userdiff: "+str(diff))
        if diff == 0:
            pass
        elif diff<0:
            for i in range(1,len(new_user_list),1):
                if new_user_list[i] not in self.specific_room_meta["users"]:
                    data = {"command":"usr-leave","item":str(new_user_list[i])}
                    self.handler(data)
        elif diff>0:
            data = {"command":"usr-join","item":new_user_list[len(new_user_list)-1]}
            self.handler(data)
        return     
    

    def handler(self,data):
        valid_requests = ["rm","add","play","pause","playback-pos","usr-join","usr-leave","queue-add","queue-alter","queue"]
        try:
            request = pickle.loads(data)
        except:
            request = data
        print(request)
        print(self.conn_list)
        if request["command"] == "timestamp":
            self.room_q.put({"kind":"timestamp","time":request["time"],"current_song":request["current_song"]})
            print("timestamp in queue")
            self.specific_room_meta["progress"] = request["time"]
            return
        if request["command"]=="usr-leave":
            print("leave")
            users = self.specific_room_meta["users"]
            print(users)
            users.remove(str(request["item"]))
            self.specific_room_meta["users"] = users
            print("current users:"+str(users))
            self.users = self.specific_room_meta["users"]
            print(self.users)
            self.room_q.put({"kind":"update_meta","meta":self.specific_room_meta})
        elif request["command"]=="queue":
            self.specific_room_meta["song_queue"] = request["item"]            
        if request["command"] in valid_requests or "meta" in request:
            for g in range(0,len(self.conn_list),1):
                print("send to:"+str(g))
                try:
                    self.conn_list[int(g)].send(pickle.dumps(request))
                except:
                    print("broken pipe...user client might have crashed")
                    del self.conn_list[int(g)]
        else:
            print("invalid request:"+str(request))
        return


if __name__=="__main__":
    multiprocessing.set_start_method('fork')
    init()
