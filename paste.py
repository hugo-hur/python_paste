import boto3
import uuid
import hashlib
import threading
import os
import sys
import time
import klembord
import magic


class ProgressBar:
    def __init__(self, total, timeEst = True, prefix = '', suffix = '', decimals = 1, length = 100, fill = '█'):
        self._total = total
        self._timeEst = timeEst
        self._prefix = prefix
        self._suffix = suffix
        self._decimals = decimals
        self._length = length
        self._fill = fill
        self._lastTime = time.perf_counter_ns()#process_time_ns()#time()
        self._lastEstimateUpdate = time.time()
        self._lastIteration = 0
    
    def update(self, iteration):
        estimate = (time.time() - self._lastEstimateUpdate > 10)
        #if time.time() - self._lastEstimateUpdate > 10:#10 seconds ago was the last estimate
        #Calculate how long it took for the iteration to complete
        #iterations/seconds
        timeLeftStr = ''
        if self._timeEst == True:
            tm = time.perf_counter_ns()#process_time_ns()#time()
            passed = tm - self._lastTime
            if passed == 0:
                print("Had to throw in a dummy time")
                passed = 0.0001
            pcPerSec = (iteration - self._lastIteration)/passed
            #print(pcPerSec)
            self._lastTime = tm
            
            #DOTO calculate weighted average of the last 10 measurements
            if self._lastIteration == 0:#First iteration
                self._lastSpeed = [pcPerSec]
            elif not estimate:#len(self._lastSpeed) < 5:#We do not have enought data yet
                #Add measurements to the list
                self._lastSpeed.append(pcPerSec)
            else:#Enought data, we want to estimate
                self._lastEstimateUpdate = time.time()
                #remove first element and append new
                #self._lastSpeed = self._lastSpeed[1:]
                #self._lastSpeed.append(pcPerSec)
                #rate = self._lastSpeed
                
                #amount = [1,2,3,4,5,6,7.5,8.2,9.5,10]
                average = sum(self._lastSpeed)/len(self._lastSpeed)#sum(x * y for x, y in zip(rate, amount)) / sum(amount)
                #timeLeftStr = str(average)
                timeLeft = (self._total - iteration)/average#pcPerSec#average
                #Clear the list
                self._lastSpeed = []
                timeLeft = timeLeft / 1000000000 #Nanoseconds to seconds
                days = timeLeft // 86400
                hours = timeLeft // 3600 % 24
                minutes = timeLeft // 60 % 60
                seconds = timeLeft % 60
                
                #timeLeftStr = str(type(timeLeft)) + "Aprox %f seconds left" % timeLeft
                timeLeftStr = "Aprox %dd %dh %dm %ds left" % (days, hours, minutes, seconds)#.format(timeLeft)#.format(int(days), int(hours), minutes, seconds) #(days, hours, minutes, seconds)#.format(timeLeft)
                #timeLeftStr = "Average %fn " % average
            
        
        
        percent = ("{0:." + str(self._decimals) + "f}").format(100 * (iteration / float(self._total)))
        filledLength = int(self._length * iteration // self._total)
        bar = self._fill * filledLength + '-' * (self._length - filledLength)
        print('\r%s |%s| %s%% %s %s' % (self._prefix, bar, percent, self._suffix, timeLeftStr), end = '\r')
        self._lastIteration = iteration
        # Print New Line on Complete
        if iteration == self._total: 
            print()

class ProgressPercentage(object):
    def __init__(self, filesize):
        #self._filename = filename
        self._size = filesize
        self._seen_so_far = 0
        self._lock = threading.Lock()
        self._progressBar = ProgressBar(self._size)
    def __call__(self, bytes_amount):
        # To simplify we'll assume this is hooked up
        # to a single filename.
        with self._lock:
            self._seen_so_far += bytes_amount
            self._progressBar.update(int(self._seen_so_far))
            sys.stdout.flush()

def deductContentType(filepath):
    contentType = magic.Magic(mime=True, mime_encoding=True).from_file(filepath)
    if "inode/blockdevice" in contentType and "mp4" in filepath:
        #We deducted wrong type for the file, should be mp4 instead
        contentType = "video/mp4; charset=binary"
    return contentType

textContentType = "text/plain; charset=utf-8"
def sendToPaste(filePath, archive=False, contentType=None, data=False):
    key = "paste/"
    if archive:
        key = "archive/"
        
    sha = hashlib.sha224()
    sha.update(str(uuid.uuid4()).encode('utf-8'))
    if not data:
        sha.update(filePath.encode('utf-8'))
    #elif contentType == "text/plain" and data:
    #    sha.update(filePath)
    else:
        sha.update(filePath)
    
    #extension = ""
    #last5 = filePath[-5:]
    extension = last5[filePath.find('.'):]
    if contentType == None:
        
        #print("ends in " + extension)
        contentType = deductContentType(filePath)
            
    else:
        #Set the proper extension
        if contentType == "image/png":
            extension = '.png'
        elif contentType == textContentType:
            extension = '.txt'
        else:
            return "Could not deduct a proper extension"
        #contentType = 'image/png'
    
    #TODO if archive, then preserve filename somehow and add key to the the filename
    if archive:#string[string.rfind(os.path.sep)+1:]
	#TODO remove the file extension from between
        filename = filePath[filePath.rfind(os.path.sep)+1:]
        filename = filename + sha.hexdigest()[-6:] + extension
    else:
        filename = 'pst' + sha.hexdigest() + extension
    print("Content type: " + contentType)
    print("Filename in bucket: "filename)
    s3 = boto3.resource('s3')
    if not data:
        s3.Bucket("paskann.us").upload_file(filePath, key + filename, ExtraArgs={'ContentType':contentType}, Callback=ProgressPercentage(float(os.path.getsize(filePath))))
    else:
        #client = boto3.client('s3')
        #client = boto3.client('s3')
        object = s3.Object('paskann.us', key + filename)
        object.put(Body=filePath, ContentType=contentType)
        """ExtraArgs={'ContentType':contentType}, Callback=ProgressPercentage(len(filePath)))"""
    print()
    return "https://paskann.us/paste/" + filename


arg = sys.argv[1]
a = False #TODO get if flag was given
if arg == 'p':
    
    data = klembord.get(["image/png","image/jpeg"])#, "CF_DSPBITMAP", "CF_BITMAP"])#, "text/plain"])
    sorted_list = [i for i in data.keys()]
    print(sorted_list)
    
    image = data['image/png']
    text = klembord.get_text()
    #print(text)
    if text != None:
        print("You pasted text")
        #print(text)
        text = text.strip(' \t\r\n\0')
        #Encode the text
        text = text.encode('utf-8')
        
        print(sendToPaste(text, archive = a, contentType=textContentType, data=True))
        
    if image != None and len(image) > 0:
        print("got image data :3")
        print(sendToPaste(image, archive = a, contentType="image/png", data=True))
        
        
else: print(sendToPaste(arg, archive = a))
