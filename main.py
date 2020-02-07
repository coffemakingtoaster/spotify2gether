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



def main():
    main_frame = tkinter.Frame(root)
    main_frame.grid()
    Label1 = tkinter.Label(main_frame,text="Create or join room").grid(row = 0,column = 1)
    e1 = tkinter.Entry(main_frame)
    e1.grid(row = 1, column=1)
    tkinter.Button(main_frame,text = "Join room",command = lambda id = e1.get():join(id,main_frame)).grid(row = 2, column=0)
    tkinter.Button(main_frame,text = "Create room").grid(row = 2, column=2)
    root.mainloop()


class check_for_user:
    def __init__(self):
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
            raise_error("Please enter username!")
            return
        scope = "user-read-playback-state streaming playlist-read-collaborative user-modify-playback-state user-read-private playlist-modify-public user-read-currently-playing playlist-read-private app-remote-control user-library-read"
        try:
            token = util.prompt_for_user_token(str(username),scope)
            print("token:"+token)
            login_frame.destroy()
            main()
        except Exception as e:
            print(str(e))
            raise_error(e)



def join(id,main_frame):

    #HOST = "127.0.0.1"
    #PORT = "696969"

    #s = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    #s.connect((HOST,PORT))
    #s.send(id.encode())
    #room_data = b""
    #BUFFER_SIZE = 1024
    #while True:
    #    received_data = s.recv(BUFFER_SIZE)
    #    room_data += received_data
    #    if len(received_data)<BUFFER_SIZE:
    #        break
    #room_meta = json.loads(room_data.decode("utf-8"))
    room_meta = {"room_name":"cosy af","room_id":"faksljn","current_song":["spotify:track:3Zigq1lfHmFRlyoRrh9k2s"],"progress": "44000"}
    #room_meta = json.loads(test_string)
    print (room_meta)
    room(room_meta,main_frame)


class room():
    def __init__(self,room_meta,main_frame):
        try:
            self.sp = spotipy.Spotify(auth=token)
        except Exception as e:
            raise_fatal_Error("No valid token! Further information: "+str(e))
        main_frame.destroy()
        room_frame = tkinter.Frame(root)
        room_frame.pack()
        self.play_pause_button = tkinter.Button(room_frame,text="II",command = self.pause_playback).pack()
        self.volume_slider = tkinter.Scale(room_frame,from_ = 0,to = 1, resolution = .1,command=self.volume_change)
        self.volume_slider.pack()
        self.button = tkinter.Button(room_frame,text="play",command = self.sp.start_playback).pack()
        json_array = json.loads(json.dumps(self.sp.devices()))
        print(json_array)
        print(json_array["devices"])
        print(json_array["devices"][0]["is_active"])
        print(json_array["devices"][0]["volume_percent"])
        self.volume_slider.set(int(json_array["devices"][0]["volume_percent"])/100)
        self.sp.transfer_playback(device_id=json_array["devices"][0]["id"],force_play=True)
        json_array = json.loads(json.dumps(self.sp.devices()))
        print(json_array["devices"][0]["is_active"])
        self.sp.start_playback(uris=room_meta["current_song"])
        x = json.loads(json.dumps(self.sp.track(room_meta["current_song"][0])))
        print(x)
        tkinter.Label(room_frame,text=str(x["album"]["artists"][0]["name"])+"-"+str(x["album"]["name"])).pack()

    def pause_playback(self):
        self.sp.pause_playback(device_id=None)
        play_pause_button.config(text="I>")


    def volume_change(self,x):
        print(str(x))
        self.sp.volume(int(float(x)*100))

    def send_change_to_server(kind,value):
        conn.sendall(str(kind)+":"+str(value))

def raise_error(Error_message):
    Error_window = tkinter.Toplevel(root)
    tkinter.Label(Error_window,text=str(Error_message))
    tkinter.Button(Error_window,text="Ok",command = Error_window.destroy)

def raise_fatal_Error(Error_message):
    fatal_Error = tkinter.Toplevel(root)
    tkinter.Label(fatal_Error,text=str(Error_message))
    tkinter.Button(fatal_Error,text="Ok and exit",command = sys.exit)


if __name__ == "__main__":
    token = ""
    os.environ["SPOTIPY_CLIENT_ID"] = "b310e9fdc45045cc9d0d6892f22beb6e"
    os.environ["SPOTIPY_CLIENT_SECRET"] = "2da1cbfd31974399b9d63c9a1f38c302"
    os.environ["SPOTIPY_REDIRECT_URI"] = "https://google.com"
    #try:
    #    token=spotipy.oauth2.SpotifyClientCredentials().get_access_token()
    #    print("token:"+str(token))
    #except Exception as e:
    #    print(e)
    root = tkinter.Tk()
    root.geometry("400x200")
    if token == "":
        token = check_for_user()
    main()
