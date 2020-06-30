import tkinter
import socket
import multiprocessing
import json
import spotipy
import os
import sys
import spotipy.util as util
from spotipy.oauth2 import SpotifyClientCredentials
import pickle
import threading
import requests
from PIL import ImageTk,Image
import time

token = ""
_FINISH = False
_PAUSE  = False
username = ""

def main():
    root.protocol("WM_DELETE_WINDOW", sys.exit)
    main_frame = tkinter.Frame(root)
    main_frame.grid()
    Label1 = tkinter.Label(main_frame,text="Create or join room").grid(row = 0,column = 1)
    id_entry = tkinter.Entry(main_frame)
    id_entry.grid(row = 1, column=1)
    tkinter.Button(main_frame,text = "Join room",command = lambda:est_conn(id_entry.get(),main_frame,"join")).grid(row = 2, column=0)
    tkinter.Button(main_frame,text = "Create room",command= lambda:est_conn(id_entry.get(),main_frame,"create")).grid(row = 2, column=2)                 
    root.mainloop()


class check_for_user:
    def __init__(self):                                                                     #opens tkinter window asking for username of spotify acc
        #read settinsgfile and if user is not found/already set then:
        global username
        self.login_frame = tkinter.Frame(root)
        self.login_frame.grid()
        tkinter.Label(self.login_frame, text = "Enter Username").grid(row=0)
        e1 = tkinter.Entry(self.login_frame)
        e1.grid(row=1,column=0)
        #tkinter.Button(self.login_frame,text="Enter",command = lambda: self.get_token(e1.get())).grid(row=1, column = 1)
        tkinter.Button(self.login_frame,text="Enter",command = lambda: check_for_user.get_token(e1.get(),self.login_frame)).grid(row=1, column = 1)
        root.mainloop()
    
    def get_token(username1,login_frame):
        global token
        global username
        username = username1
        print(str(username))
        if username=="":
            raise_error("Please enter username!")                   #raises error for empty username
            return
        #scope has to be passed to spotify api this determines what the application will be able to do
        scope = "user-read-playback-state streaming playlist-read-collaborative streaming user-modify-playback-state user-read-private playlist-modify-public user-read-currently-playing playlist-read-private app-remote-control user-library-read"
        try:
            print(username)
            token = util.prompt_for_user_token(username,scope=scope,show_dialog=True)    #call to spotify api to get token
            print("token:"+token)
            print(spotipy.Spotify(auth=token).me())
            login_frame.destroy()                                       #if successful window gets destroyed (now main funntion will start)
            x = os.getcwd()   
            if os.path.exists("sp_tmp") is not True:
                os.mkdir("sp_tmp")    
            os.chdir(os.path.join(x,"sp_tmp"))  
            print(os.getcwd())  
            main()
        except Exception as e:                                          #catches error and forwards it to raise_error class
            print(str(e))
            raise_error(e)



def est_conn(id,main_frame,cmd):                                  #establish connection to server
    print("entered room id:"+str(id))
    HOST = "HOST_IP"
    PORT = "HOST PORT"
    print("trying to join")
    s = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    try:
        s.connect((HOST,PORT))
    except:
        raise_fatal_Error("Connection to sever could not be established!")
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
        id = s.recv(1024)
        readable_id = pickle.loads(id)
        print(readable_id["id"])
        room_id = readable_id["id"]
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
        else:
            room_id = id
    print (room_meta)
    room(room_meta,main_frame,s,room_id)

    
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
    def __init__(self,room_meta,main_frame,s,rID):                                                #displays room
        global _FINISH 
        _FINISH = False
        try:
            self.sp = spotipy.Spotify(auth=token)
        except Exception as e:
            raise_fatal_Error("No valid token! Further information: "+str(e))               #raises fatal error! See difference between raise_error and raise_fatal_Error below
        main_frame.destroy()
        room_frame = tkinter.Frame(root)
        self.s = s
        room_frame.grid()
        self.room_meta = room_meta
        self.current_song_title = tkinter.StringVar()
        self.current_artist = tkinter.StringVar()
        self.current_song_image = ""  
        while True:
            print("trying")
            try:
                self.sp.start_playback(uris=room_meta["current_song"])
                break
            except:
                raise_error("No active playback")
        json_array = json.loads(json.dumps(self.sp.devices()))              
        if room_meta["is_playing"] is True:
            self.playback_state = 1
        else:
            self.sp.pause_playback()
            self.playback_state = 0
        self.play_state_display = tkinter.StringVar()
        self.play_state_display.set("II")
        self.progress_time_var = tkinter.StringVar()
        self.progress_time_var.set("00:00/00:00")
        try:
            self.queue = room_meta["song_queue"]
        except:
            self.queue = []
        self.queue_window = tkinter.Toplevel(root)
        self.queue_view_frame = tkinter.Frame(self.queue_window)
        self.queue_view = tkinter.Listbox(self.queue_view_frame)
        self.queue_window.overrideredirect(1)
        self.queue_is_shown = 0
        self.queue_is_init = 0
        self.queue_window.withdraw()
        
        # visualization...
        self.leave_button = tkinter.Button(room_frame,text="leave room",command = lambda room_frame = room_frame:self.leave(room_frame))
        self.room_id_button = tkinter.Button(room_frame, text = "Copy room ID",command = lambda rID = rID: self.copy_to_clipboard(rID))
        self.song_image_label = tkinter.Label(room_frame,image = self.current_song_image)
        self.current_song_display = tkinter.Label(room_frame,textvariable=self.current_song_title)  #displays song name 
        self.current_artist_display = tkinter.Label(room_frame,textvariable=self.current_artist) 
        self.volume_slider = tkinter.Scale(room_frame,from_ = 1,to = 0, resolution = .1,command=self.volume_change)  
        self.play_pause_button = tkinter.Button(room_frame,textvariable=self.play_state_display,command = self.send_playback_change)        
        self.play_song = tkinter.Entry(room_frame)     
        self.play_song_button = tkinter.Button(room_frame,text="Add to Queue",command=lambda: self.add_to_queue(self.play_song.get()))
        self.playback_progress_time_Label = tkinter.Label(room_frame,textvariable = self.progress_time_var)
        self.progress_bar = tkinter.Canvas(room_frame,width=300,height=20)
        self.queue_button = tkinter.Button(room_frame,text = "Queue",command=self.show_queue)
        
        #layout section grid is used
        self.leave_button.grid(row = 0,column=3)
        self.room_id_button.grid(row=0,column=1)
        self.song_image_label.grid(row=1,rowspan = 2,column=0,columnspan = 2)
        self.current_song_display.grid(row=1,column=2)
        self.current_artist_display.grid(row=2,column=2)
        self.volume_slider.grid(row = 1,rowspan = 2,column = 3)
        self.play_pause_button.grid(row = 4,column=1)
        self.progress_bar.grid(row=3,column = 0, columnspan = 4)
        self.playback_progress_time_Label.grid(row = 4,column=3)   
        self.play_song.grid(row = 5,column = 1,columnspan=2)
        self.play_song_button.grid(row=5,column=3)
        self.queue_button.grid(row=4, column=0)
        
        #last init
        x = json.loads(json.dumps(self.sp.track(self.room_meta["current_song"][0])))
        self.volume_slider.set(int(json_array["devices"][0]["volume_percent"])/100)             #get current volume and change value of slide accordingly        
        self.update_song_visuals(token,song_meta=x)                                                         #song display (image+name) set
        x1 = int(x["duration_ms"])/1000
        cache01 = 0
        while x1 > 60:
            cache01 = cache01+1
            x1 = x1-60
        cache02 = str(round(x1))    
        if len(cache02)==1:
            cache02 = "0"+cache02
        print(str(cache01)+":"+str(cache02))
        if int(self.room_meta["progress"])==0:
            self.progress_time_var.set("00:00/"+str(cache01)+":"+str(cache02))
        else:
            current_timestamp = int(self.room_meta["progress"])/1000
            current_min = 0
            while current_timestamp>60:
                current_min+=1
                current_timestamp = current_timestamp-60
            current_sec = round(current_timestamp)
            if int(current_sec)<10:
                current_sec = "0"+str(current_sec)
            self.progress_time_var.set(str(current_min)+":"+str(current_sec)+"/"+str(cache01)+":"+str(cache02))

        
        
        #start song progress bar
        _PAUSE = False
        progress_bar = threading.Thread(target=self.visualize_song_progress,args=(x,))
        progress_bar.start()
               
        # start server listener
        _FINISH = False
        self.bkground = threading.Thread(target=self.room_listener,args=())
        self.bkground.start()
    
    
    # queue controlling stuff start
    def add_to_queue(self,new_song_uri):
        x = self.sp.track(new_song_uri)
        print(x)
        add_this = str(x["album"]["artists"][0]["name"])+"-"+str(x["album"]["name"])
        print(add_this)
        self.queue.append(new_song_uri)
        self.queue.append(add_this)
        print("added")
        print(self.queue)
        print("add")
        self.s.sendall(pickle.dumps({"command":"queue","item":self.queue}))
        print("send")
        self.play_song.delete(0,tkinter.END)
    
    def show_queue(self,new_queue = None,hide_queue=False):
        if new_queue is not None:
            print("new_queue",new_queue)
            self.queue = new_queue
        if self.queue_is_init == 0:
            self.queue_view.__init__(master = self.queue_view_frame)
            self.queue_view.bind("<Button-1>",self.getstate, add = "+")
            self.queue_view.bind("<Button-1>",self.setcurrent, add = "+")
            self.queue_view.bind("<B1-Motion>",self.shiftseletion)
            self.queue_view_frame.pack()
            tkinter.Button(self.queue_window,text="Close",command = self.hide_queue).pack()
            tkinter.Button(self.queue_window,text="Del",command = self.delete_from_queue).pack()
            self.empty_queue = tkinter.Label(self.queue_view_frame,text="Queue is empty")
            self.queue_view.pack()
            self.queue_is_init = 1
        if self.queue_is_shown == 0 and hide_queue==False:
            self.queue_window.update()
            self.queue_window.deiconify()
            self.queue_is_shown = 1
        self.queue_view.delete(0,tkinter.END)
        if len(self.queue) == 0:
            if not self.empty_queue.winfo_ismapped():
                self.empty_queue.pack()
        else:
            if self.empty_queue.winfo_ismapped():
                self.empty_queue.pack_forget()
            print("cleared")
            i = 1
            for g in range(1,len(self.queue),2):
                self.queue_view.insert(tkinter.END,str(i)+" "+str(self.queue[g]))   #out of range
                i +=1     
        self.curIndex = 0
        self.curState = 0

        
        
    def delete_from_queue(self):
        i = self.curIndex
        z = self.queue_view.get(i)
        index = None
        for i in range(0,len(self.queue),1):
            print(z[len(str(i/2))+1:])
            print(self.queue[i])
            if z[len(str(i/2))+1:] in self.queue[i]:
                index = i
                break    
        self.curIndex = 1
        print("del")
        if index:
            del self.queue[i]
            del self.queue[i-1]  
        self.s.sendall(pickle.dumps({"command":"queue","item":self.queue}))
        
    def hide_queue(self):
        self.queue_window.withdraw()
        self.queue_is_shown = 0
        
    def setcurrent(self,event):
        self.curIndex = self.queue_view.nearest(event.y)
    
    def getstate(self,event):
        i = self.queue_view.nearest(event.y)
        self.curState = self.queue_view.selection_includes(i)
        
    def shiftseletion(self,event):
        change = None
        i = self.queue_view.nearest(event.y)
        if self.curState == 1:
            self.queue_view.selection_set(self.curIndex)
        else:
            self.queue_view.selection_clear(self.curIndex)        
        if i<self.curIndex:
            print("up")
            x = self.queue_view.get(i)
            print(x)
            selected_item = self.queue_view.selection_includes(i)
            self.queue_view.delete(i)
            self.queue_view.insert(i+1,x)
            if selected_item:
                self.queue_view.selection_set(i+1)
            self.curIndex = 1
            new_queue = []
            for i in range(0,len(self.queue),2):
                if self.queue[i]==x:
                    new_queue.insert(i-3,self.queue[i-1])
                    new_queue.insert(i-2,self.queue[i])
                else:
                    new_queue.append(self.queue[i])
                    new_queue.append(self.queue[i-1])
        elif i>self.curIndex:
            x = self.queue_view.get(i)
            print(x)
            selected_item = self.queue_view.selection_includes(i)
            self.queue_view.delete(i)
            self.queue_view.insert(i-1,x)
            if selected_item:
                self.queue_view.selection_set(i-1)
            self.curIndex = 1
            new_queue = []
            index = None
            for i in range(0,len(self.queue),2):
                if self.queue[i]==x:
                    index = i
                else:
                    new_queue.append(self.queue[i])
                    new_queue.append(self.queue[i-1])
            if index:
                print(index)
                new_queue.insert(index-3,self.queue[index])
                new_queue.insert(index-2,self.queue[index-1])
        else:
            return
        print(new_queue )   
        self.show_queue(new_queue=new_queue)
        self.s.sendall(pickle.dumps({"command":"queue","item":self.queue}))
        
             
    #queue controlling stuff end   
        
    #progress bar and timestamp start     
    
    def visualize_song_progress(self,song_meta):
        self.bar = self.progress_bar.create_rectangle(0,0,300,20,outline ="#335bff",fill= "#ffffff")
        self.actual_progress = self.progress_bar.create_rectangle(0,0,0,20,fill = "#335bff")
        song_length_cache = self.progress_time_var.get()
        total_song_length = int(song_meta["duration_ms"])/1000
        print(total_song_length)
        playing_id = song_meta["album"]["uri"]
        self._selected = False
        self.progress_bar.bind("<Button-1>",self.change_timestamp)
        while True:
            if _FINISH:
                break
            if self.playback_state == 0:
                print("paused")
                while self.playback_state == 0:
                    time.sleep(0.1)       
            else:
                cache01,cache02 = self.progress_time_var.get().split("/")
                minutes,sec = cache01.split(":")
                total_minutes,total_seconds = cache02.split(":")
                if int(total_minutes)==int(minutes) and int(total_seconds)-int(sec)<=0:
                    if len(self.queue)!=0:
                        x = self.queue[0]
                        songs = []
                        songs.append(x)
                    else :
                        songs = self.room_meta["current_song"]
                    print(songs)
                    #self.room_meta["current_song"] = x
                    self.sp.start_playback(uris=songs)
                    x = self.sp.track(songs[0])
                    self.update_song_visuals(songs)                     
                    x = int(x["duration_ms"])/1000
                    total_song_length = x
                    cache01 = 0
                    while x > 60:
                        cache01 = cache01+1
                        x = x-60
                    cache02 = str(round(x))    
                    if len(cache02)==1:
                        cache02 = "0"+cache02
                    print(str(cache01)+":"+str(cache02))  
                    self.progress_time_var.set("00:00/"+str(cache01)+":"+str(cache02))
                    print(self.progress_time_var.get())
                    print(self.queue)
                    if len(self.queue)>=2:
                        del self.queue[1]
                        del self.queue[0]
                    print("this queue after fetching:"+str(self.queue))
                    if self.queue_is_shown == 0:
                        self.show_queue(hide_queue=True)
                    minutes = 0
                    self.room_meta["current_song"]=songs
                    sec = 0     
                    self.update_song_visuals()
                    cache02 = str(cache01)+":"+str(cache02)
                    self.queue_view.delete(0)                   
                current_time = int(minutes)*60+int(sec)
                self.progress_bar.coords(self.actual_progress,0,0,current_time/total_song_length*300,20)
                print(round(current_time/total_song_length))
                sec = int(sec)+1
                if sec<10:
                    sec = "0"+str(sec)
                elif sec==60:
                    minutes = int(minutes)+1
                    sec = "00"
                self.progress_time_var.set(str(minutes)+":"+str(sec)+"/"+str(cache02))
                current_cache = str(minutes)+":"+str(sec)+"/"+str(cache02)
                print(self.progress_time_var.get())
                time.sleep(1)
            
    def change_timestamp(self,event):
        c1,c2 = self.progress_time_var.get().split("/")
        minutes, seconds = c2.split(":")
        print(minutes)
        print(seconds)
        current_song_length = int(minutes)*60+int(seconds)
        print(current_song_length)
        print("clicked at"+ str(event.x))
        print(event.x/300)
        timestamp = round((event.x/300)*int(current_song_length))*1000
        self.s.sendall(pickle.dumps({"command":"playback-pos","item":timestamp}))
                   
    def update_song_visuals(self,uri=None,song_meta=None):
        print(uri)
        print(song_meta)
        if uri is None:
            uri = self.room_meta["current_song"]           
        if song_meta is None:
            song_meta = json.loads(json.dumps(self.sp.track(uri[0])))
        x = song_meta   
        print(x)
        title =str(x["album"]["name"])
        artist = str(x["album"]["artists"][0]["name"])
        print(artist)
        if len(title)>15:
            title = title[:12]+"..."
        self.current_song_title.set(title)
        self.current_artist.set(artist)
        pic_name = str(str(uri[0])[14:]+".jpg")
        if os.path.isfile(pic_name):
            self.current_song_image = ImageTk.PhotoImage(Image.open(pic_name))
            self.song_image_label.configure(image=self.current_song_image)
            self.song_image_label.image = self.current_song_image   #anti-garbage collector      
            return       
        for item in x["album"]["images"]:
            print(item)
            if int(item["height"]) == 64:
                image_url = str(item["url"])
                print("URL:"+str(image_url))
                break
        with open(pic_name, 'wb') as handle:
            response = requests.get(image_url, stream=True)
            if not response.ok:
                print (response)
            for block in response.iter_content(1024):
                if not block:
                    break
                handle.write(block)
        self.current_song_image = ImageTk.PhotoImage(Image.open(pic_name))
        print(self.song_image_label)
        self.song_image_label.configure(image=self.current_song_image)
        self.song_image_label.image = self.current_song_image   #anti-garbage collector
        
    #visuals and timestamp end
        
    
    # server client communication  
    def handle_command(self,received_command):                                                           #function that handles requests from server
        print(received_command)
        cmd = received_command["command"]
        print("received "+str(cmd))
        if cmd=="play":
            if received_command["item"]!=self.room_meta["current_song"]:
                songs = []
                songs.append(received_command["item"][0])
                self.sp.start_playback(uris=songs)
                self.playback_state = 1
                self.update_song_visuals(token,songs)
                x = self.sp.track(received_command["item"][0])["duration_ms"]
                x = x/1000
                cache01 = 0
                while x > 60:
                    cache01 = cache01+1
                    x = x-60
                cache02 = str(round(x))    
                if len(cache02)==1:
                    cache02 = "0"+cache02
                print(str(cache01)+":"+str(cache02))  
                self.progress_time_var.set("00:00/"+str(cache01)+":"+str(cache02))               
            else:
                self.alter_playback(force_mode=1)
                self.playback_state = 1
        elif cmd=="pause":
            self.alter_playback(force_mode=0)
        elif cmd=="playback-pos":
            try:
                self.sp.seek_track(position_ms=int(received_command["item"]))
                x = int(received_command["item"])/1000
                print("this is"+str(x))
                cache01 = 0
                while x > 60:
                    cache01 = cache01+1
                    x = x-60
                cache02 = str(round(x))    
                if len(cache02)==1:
                    cache02 = "0"+cache02
                print(str(cache01)+":"+str(cache02))
                temp1,temp2 = self.progress_time_var.get().split("/")
                self.progress_time_var.set(str(cache01)+":"+str(cache02)+"/"+str(temp2))
            except Exception as e:
                print(e)
        elif cmd == "queue":
            print("changing queue")
            self.queue_view.selection_clear(0,tkinter.END)
            x = received_command["item"]
            print(x)
            self.show_queue(new_queue=x)
            #self.queue = received_command["item"]
            #i = 1
            #self.queue_view.selection_clear(0,tkinter.END)
            #no = 1
            #for i in range(0,len(self.queue),2):
            #    self.queue_view.insert(tkinter.END,str(no)+" "+str(self.queue[i]))
            #    print(self.queue[i])
            #    no+=1
            #print("arranged listview")
        elif cmd == "alive":
            self.s.sendall(pickle.dumps({"answer":"yes"}))
        elif cmd=="timestamp":
            cache01,cache02 = self.progress_time_var.get().split("/")
            minutes, seconds = cache01.split(":")
            timestamp = ((60*int(minutes))+int(seconds))*1000
            print(timestamp)
            self.s.sendall(pickle.dumps({"command":"timestamp","time":timestamp,"current_song":[self.room_meta["current_song"]]}))
            
   
    def room_listener(self):                                                              #function that receives server commands
        global _FINISH
        conn_to_server = self.s
        self.s.settimeout(1)
        data = b""
        while True:
            print(_FINISH)
            if _FINISH is True:
                print("background break")
                break
            print("listening")
            try:
                datachunk = conn_to_server.recv(1024)
            except:
                datachunk = None
                print("timed out")
            if datachunk:
                data += datachunk
            if datachunk == None:
                pass
            elif len(datachunk)<1024:
                command_from_server = pickle.loads(data)   
                print(command_from_server) 
                self.handle_command(command_from_server)
                data= b""
    
    def send_playback_change(self):
        x = self.sp.current_playback()
        print(x)
        if x["is_playing"]==True:
            self.s.sendall(pickle.dumps({"command":"pause"}))
            print("send pause")
        else:
            self.s.sendall(pickle.dumps({"command":"play","item":self.room_meta["current_song"]}))
            print("send play")
            
            
    # communication end
    
    # UI and playback func start
    def alter_playback(self,force_mode=None):   
        print("called")     
        global token         
        sp = spotipy.Spotify(auth=token)                     	                           
        if force_mode == self.playback_state:
            return
        if self.playback_state == 1:
            sp.pause_playback(device_id=None)
            self.play_state_display.set("I>")
            self.playback_state = 0
        else:
            sp.start_playback(device_id=None)
            self.play_state_display.set("II")
            self.playback_state = 1

    def volume_change(self,x):                                                                   #obvious
        self.sp.volume(int(float(x)*100))
        

    def leave(self,room_frame):
        global _FINISH
        _FINISH = True
        x = pickle.dumps({"command":"usr-leave","item":str(username)})
        len(x)
        self.s.sendall(pickle.dumps({"command":"usr-leave","item":str(username)}))
        self.s.close()
        self.queue_window.destroy()
        room_frame.destroy()
        main()

    def play(self,song):                                                                         #plays new song and changes display label- May also be called by queue
        song_uri = []
        song_uri.append(song)
        self.sp.start_playback(uris=song_uri)
        x = json.loads(json.dumps(self.sp.track(room_meta["current_song"][0])))
        self.current_song_display.set(str(x["album"]["artists"][0]["name"])+"-"+str(x["album"]["name"]))

        
    def copy_to_clipboard(self,rID):
        root.clipboard_clear()
        root.clipboard_append(str(rID))
        return

    def play_new_song(self,song_uri):
        try:
            self.sp.track(song_uri)
        except:
            raise_error("Invalid uri")
            return
        songs = []
        songs.append(song_uri)
        self.s.sendall(pickle.dumps({"command":"play","item":songs}))
        print("send song to play")
        self.sp.start_playback(uris=songs)

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
        

def raise_error(Error_message):                                                                 #raise errors. This function is used for errors that do not require the program to shut down
    Error_window = tkinter.Toplevel(root)
    tkinter.Label(Error_window,text=str(Error_message)).pack()
    tkinter.Button(Error_window,text="Ok",command = Error_window.destroy).pack()
    root.wait_window(Error_window)

def raise_fatal_Error(Error_message):                                                           #raise errors that require the app to close. Directly calls sys.exit()
    fatal_Error = tkinter.Toplevel(root)
    tkinter.Label(fatal_Error,text=str(Error_message))
    tkinter.Button(fatal_Error,text="Ok and exit",command = sys.exit)


def disable_event():
    filelist = [f for f in os.listdir("sp_tmp")]
    for file in filelist:
        os.remove(os.path.join("sp_tmp",f))
    print("tmp files deleted")
    _FINISH = True 
    try:
        bkground.join()
    except:
        pass
    sys.exit()                           

if __name__ == "__main__":
    os.environ["SPOTIPY_CLIENT_ID"] = "SPOTIPY_CLIENT_ID"                        # initalizes app-client-values. Idealy those should be hidden from user
    os.environ["SPOTIPY_CLIENT_SECRET"] = "SPOTIPY_CLIENT_SECRET"                    # and pulled from a server rather than being hard-coded
    os.environ["SPOTIPY_REDIRECT_URI"] = "SPOTIPY_REDIRECT_URI    
    #try:
    #    token=spotipy.oauth2.SpotifyClientCredentials().get_access_token()                      #checks for existing token and alters value of token variable
    #    print("found token:"+str(token))
    #except Exception as e:
    #    print(e)
    root = tkinter.Tk()
    root.geometry("400x250")
    root.protocol("WM_DELETE_WINDOW", disable_event)
    root.resizable(False, False)
    if token == "":
        print("checking for user")
        check_for_user()                                                                #if no token exists function is called

