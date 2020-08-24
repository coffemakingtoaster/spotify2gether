import spotipy
from tkinter import Toplevel,Label,Button


class room_helper:
    def generate_room_meta(self,room_name,token):
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

class Error_handler():
    def __init__(self,root):
        self.root = root

    def raise_error(Error_message,root):                                                                 #raise errors. This function is used for errors that do not require the program to shut down
        Error_window = tkinter.Toplevel(root)
        tkinter.Label(Error_window,text=str(Error_message)).pack()
        tkinter.Button(Error_window,text="Ok",command = Error_window.destroy).pack()
        root.wait_window(Error_window)
    
    
    def raise_fatal_Error(Error_message,root):                                                           #raise errors that require the app to close. Directly calls sys.exit()
        fatal_Error = tkinter.Toplevel(root)
        tkinter.Label(fatal_Error,text=str(Error_message))
        tkinter.Button(fatal_Error,text="Ok and exit",command = sys.exit)