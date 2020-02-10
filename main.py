import tkinter
import socket
import multiprocessing
import json
import spotipy
import os
import sys
import spotipy.util as util
from spotipy.oauth2 import SpotifyClientCredentials
import requests
import pickle


def main():
    main_frame = tkinter.Frame(root)
    main_frame.grid()
    Label1 = tkinter.Label(main_frame,text="Create or join room").grid(row = 0,column = 1)
    id_entry = tkinter.Entry(main_frame)
    id_entry.grid(row = 1, column=1)
    tkinter.Button(main_frame,text = "Join room",command = lambda:est_conn(id_entry.get(),main_frame,"join")).grid(row = 2, column=0)
    tkinter.Button(main_frame,text = "Create room",command= lambda:est_conn(id_entry.get(),main_frame,"create")).grid(row = 2, column=2)                  #currently lacks funtionality (serverside as well)
    root.mainloop()


class check_for_user:
    def __init__(self):                                                                     #opens tkinter window asking for username of spotify acc
        #read settinsgfile and if user is not found/already set then:
        self.login_frame = tkinter.Frame(root)
        self.login_frame.grid()
        tkinter.Label(self.login_frame, text = "Enter Username").grid(row=0)
        e1 = tkinter.Entry(self.login_frame)
        e1.grid(row=1,column=0)
        #tkinter.Button(self.login_frame,text="Enter",command = lambda: self.get_token(e1.get())).grid(row=1, column = 1)
        tkinter.Button(self.login_frame,text="Enter",command = lambda: check_for_user.get_token(e1.get(),self.login_frame)).grid(row=1, column = 1)
        root.mainloop()

    def get_token(username,login_frame):
        global token
        print(str(username))
        if username=="":
            raise_error("Please enter username!")                   #raises error for empty username
            return
        #scope has to be passed to spotify api this determines what the application will be able to do
        scope = "user-read-playback-state streaming playlist-read-collaborative user-modify-playback-state user-read-private playlist-modify-public user-read-currently-playing playlist-read-private app-remote-control user-library-read"
        try:
            token = util.prompt_for_user_token(str(username),scope)     #call to spotify api to get token
            print("token:"+token)
            login_frame.destroy()                                       #if successful window gets destroyed (now main funntion will start)
            main()
        except Exception as e:                                          #catches error and forwards it to raise_error class
            print(str(e))
            raise_error(e)



def est_conn(id,main_frame,cmd):                                  #establish connection to server
    print("entered room id:"+str(id))
    HOST = "185.16.60.254"
    PORT = 8000
    print("trying to join")
    s = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    s.connect((HOST,PORT))
    payload = {"command":str(cmd)}
    if cmd=="create":
        room_meta = generate_room_meta(id)
        payload["room_meta"] = room_meta
    else:
        payload["id"]=str(id)
        payload["name"]=str(spotipy.Spotify(auth=token).current_user()["display_name"])
    print("connected")
    s.send(pickle.dumps(payload))
    print("send "+str(payload))
    if cmd=="create":
        id = s.recv(8)
        print(id)
    else:
        room_data = b""
        BUFFER_SIZE = 1024
        while True:
            received_data = s.recv(BUFFER_SIZE)
            print(received_data)
            room_data += received_data
            if len(received_data)<BUFFER_SIZE and room_data != b"":
                break
        room_meta = pickle.loads(room_data)      #loads received data into usable form...might change to pickle rather than json
        if room_meta["state"]=="invalid":
            raise_error("invalid room id")
            return
    print (room_meta)
    room(room_meta,main_frame,s)
    server_listener = multiprocessing.Process(target=room_listener,args=(s,))               #starts seperate process that listens to server and therefore commands from other users
    server_listener.start()

def generate_room_meta(room_name):
    sp = spotipy.Spotify(auth=token)
    songs = []
    #song = sp.currently_playing(market=None)
    song = "spotify:track:3Zigq1lfHmFRlyoRrh9k2s"
    print(song)
    songs.append(song)
    #songs.append(song[context][uri])
    users = []
    x = sp.me()["display_name"]
    print(x)
    users.append(x)
    timestamp = "00000"
    room_meta = {"room_name":str(room_name),"current_song":songs,"progress":timestamp,"users":users,"is_playing":True}
    return room_meta




class room():
    def __init__(self,room_meta,main_frame,s):                                                #displays room
        try:
            self.sp = spotipy.Spotify(auth=token)
        except Exception as e:
            raise_fatal_Error("No valid token! Further information: "+str(e))               #raises fatal error! See difference between raise_error and raise_fatal_Error below
        main_frame.destroy()
        room_frame = tkinter.Frame(root)
        self.s = s
        room_frame.pack()
        self.room_meta = room_meta
        self.play_pause_button = tkinter.Button(room_frame,text="II",command = self.alter_playback).pack()
        self.volume_slider = tkinter.Scale(room_frame,from_ = 0,to = 1, resolution = .1,command=self.volume_change)
        self.volume_slider.pack()
        #self.button = tkinter.Button(room_frame,text="play",command = self.sp.start_playback).pack()
        json_array = json.loads(json.dumps(self.sp.devices()))
        print(json_array)
        print(json_array["devices"])
        print(json_array["devices"][0]["is_active"])
        print(json_array["devices"][0]["volume_percent"])
        self.volume_slider.set(int(json_array["devices"][0]["volume_percent"])/100)             #get current volume and change value of slide accordingly
        self.sp.transfer_playback(device_id=json_array["devices"][0]["id"],force_play=True)     #avoid "no active devices" error
        json_array = json.loads(json.dumps(self.sp.devices()))                                  #depending on situation a device selection might be necessary
        print(json_array["devices"][0]["is_active"])                                            #checks if setting device to active was successful
        if room_meta["is_playing"] is True:
            self.sp.start_playback(uris=room_meta["current_song"])
            self.playback_state = 1
        else:
            self.sp.start_playback(uris=room_meta["current_song"])
            self.sp.pause_playback()
            self.playback_state = 1
        x = json.loads(json.dumps(self.sp.track(room_meta["current_song"][0])))
        print(x)
        self.current_song_display = tkinter.Label(room_frame,text=str(x["album"]["artists"][0]["name"])+"-"+str(x["album"]["name"])).pack()  #displays artist and song name
        self.play_song = tkinter.Entry(room_frame)
        self.play_song.pack()
        tkinter.Button(room_frame,text="Play song",command=lambda: play_new_song(self.play_song.get()))

    def alter_playback(self,force_mode=None):                                   	                           #function changes playback state. uses self.playback_state to determine current playback state
        if force_mode is not None:
            self.playback_state = force_mode
        if self.playback_state == 1:
            s.sendall(pickle.dump({"command":"pause"}))
            self.sp.pause_playback(device_id=None)
            play_pause_button.config(text="I>")
            self.playback_state = 0
        else:
            s.sendall(pickle.dump({"command":"play","item":str(room_meta["current_song"])}))
            self.sp.start_playback(device_id=None)
            play_pause_button.config(text="II")
            self.playback_state = 1

    def volume_change(self,x):                                                                   #obvious
        print(str(x))
        self.sp.volume(int(float(x)*100))


    def play(self,song):                                                                         #plays new song and changes display label- May also be called by queue
        song_uri = []
        song_uri.append(song)
        self.sp.start_playback(uris=song_uri)
        x = json.loads(json.dumps(self.sp.track(room_meta["current_song"][0])))
        self.current_song_display.set(str(x["album"]["artists"][0]["name"])+"-"+str(x["album"]["name"]))

    def send_current_timestamp(timestamp):
        s.sendall(pickle.dumps(timestamp))

    def play_new_song(song_uri):
        try:
            self.sp.track(song_uri)
        except:
            raise_error("Invalid uri")
            return
        songs = []
        songs.append(song_uri)
        s.sendall(pickle.loads({"command":"play","item":songs}))
        sp.start_playback(uris=songs)

    def add_user(username):
        self.room_meta["users"].append(username)
        user_list = ""
        for item in room_meta["users"]:
            user_list+=str(item)+","
        self.user_list_label.set(text=user_list)
        return

    def rm_user(self,username):
        self.room_meta["users"].remove(username)
        user_list = ""
        for item in room_meta["users"]:
            user_list+=str(item)+","
        self.user_list_label.set(text=user_list)
        return

     def alter_playback_timestamp(self):
         pass

    def send_current_timestamp(self,timestamp):
        s.sendall(pickle.dumps({"time":timestamp})
        return


def room_listener(conn_to_server):                                                              #function that receives server commands
    while True:
        datachunk = conn_to_server.recv(1024)
        if datachunk:
            data = datachunk
            while True:
                datachunk = conn_to_server.recv(1024)
                if not datachunk:
                    handle_command(pickle.loads(data))
                    break
                data += datachunk


def handle_command(received_command):                                                           #function that handles requests from server
    cmd = received_command["command"]
    if cmd=="play":
        room.play(received_command["item"])
    elif cmd=="pause":
        spotipy.Spotify(auth=token).alter_playback(force_mode=1)
    elif cmd=="playback-pos":
        spotipy.Spotify(auth=token).start_playback(offset=int(received_command["item"]))
    elif cmd=="usr-join":
        room.add_user(str(received_command["item"]))
    elif cmd=="usr-leave":
        room.rm_user(str(received_command["item"]))
    elif cmd=="timestamp":
        room.send_current_timestamp(spotipy.Spotify(auth=token).current_playback()["progress_ms"])



def raise_error(Error_message):                                                                 #raise errors. This function is used for errors that do not require the program to shut down
    Error_window = tkinter.Toplevel(root)
    tkinter.Label(Error_window,text=str(Error_message))
    tkinter.Button(Error_window,text="Ok",command = Error_window.destroy)

def raise_fatal_Error(Error_message):                                                           #raise errors that require the app to close. Directly calls sys.exit()
    fatal_Error = tkinter.Toplevel(root)
    tkinter.Label(fatal_Error,text=str(Error_message))
    tkinter.Button(fatal_Error,text="Ok and exit",command = sys.exit)


if __name__ == "__main__":
    token = ""
    os.environ["SPOTIPY_CLIENT_ID"] = "b310e9fdc45045cc9d0d6892f22beb6e"                        # initalizes app-client-values. Idealy those should be hidden from user
    os.environ["SPOTIPY_CLIENT_SECRET"] = "2da1cbfd31974399b9d63c9a1f38c302"                    # and pulled from a server rather than being hard-coded
    os.environ["SPOTIPY_REDIRECT_URI"] = "https://google.com"
    #try:
    #    token=spotipy.oauth2.SpotifyClientCredentials().get_access_token()                      #checks for existing token and alters value of token variable
    #    print("found token:"+str(token))
    #except Exception as e:
    #    print(e)
    root = tkinter.Tk()
    root.geometry("400x200")
    if token == "":
        token = check_for_user()                                                                #if no token exists function is called
    main()
