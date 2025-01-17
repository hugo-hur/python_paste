import boto3
import uuid
import hashlib
import threading
import os
import sys
import time
import klembord
import magic
import argparse
import glob

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
        self._progressBar = ProgressBar(self._size, length = 50)
    def __call__(self, bytes_amount):
        # To simplify we'll assume this is hooked up
        # to a single filename.
        with self._lock:
            self._seen_so_far += bytes_amount
            self._progressBar.update(int(self._seen_so_far))
            sys.stdout.flush()

def deductContentType(filepath):
    #contentType = magic.Magic(mime=True, mime_encoding=True).from_file(filepath)
    with open(filepath, "rb") as file:
        contentType = magic.Magic(mime=True, mime_encoding=True).from_buffer(file.read())
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
    extension = ""
    if contentType == None and not data:
        extension = filePath[filePath.rfind('.'):]
        #print("ends in " + extension)
        contentType = deductContentType(filePath)
            
    else:
        #Set the proper extension
        if contentType == "image/png":
            extension = '.png'
        elif contentType == "image/jpeg":
            extension = '.jpg'
        elif contentType == textContentType:
            extension = '.txt'
        else:
            return "Could not deduct a proper extension"
        #contentType = 'image/png'
    
    #TODO if archive, then preserve filename somehow and add key to the the filename
    if archive and not data:#string[string.rfind(os.path.sep)+1:]
	#Remove the file extension from between
        
        filename = filePath[filePath.rfind(os.path.sep)+1:]
        tp = os.path.splitext(filename)
        filename = tp[0] + ' ' + sha.hexdigest()[-6:] + tp[1]
    elif archive and data:#We got  data in and  want to archive it, add add a prefix to name
        filename = "paste" + sha.hexdigest()[-6:] + extension
    else:#Not archiving
        filename = 'pst' + sha.hexdigest() + extension
        
    print("Content type: " + contentType)
    filename = key + filename
    print("Filename in bucket: " + filename)
    s3 = boto3.resource('s3')
    if not data:
        s3.Bucket("paskann.us").upload_file(filePath, filename, ExtraArgs={'ContentType':contentType}, Callback=ProgressPercentage(float(os.path.getsize(filePath))))
    else:
        #client = boto3.client('s3')
        #client = boto3.client('s3')
        object = s3.Object('paskann.us', filename)
        object.put(Body=filePath, ContentType=contentType)
        """ExtraArgs={'ContentType':contentType}, Callback=ProgressPercentage(len(filePath)))"""
    print()
    return "https://paskann.us/" + filename


parser = argparse.ArgumentParser(description='Paste data from clipboard or upload a file to s3')
parser.add_argument('-p', '--paste', help='Use data from clipboard (choose clipboard)', action="store_true")
parser.add_argument('-a', '--archive', help='If set, send the data to archive instead of standard storage tier', action="store_true")
parser.add_argument('-r', '--recursive', help='If set will recursively traverse all matching paths', action="store_true")
parser.add_argument('-f', '--file', help='Path to file or directory to upload (choose file)')
args = parser.parse_args()
print(args)
#exit()

files = []
folders = []
matches = ''
if not args.paste and args.file == None:
    print("Error: you have to specify either a file to upload or the '-p' flag to use the clipboard contents.")
    exit()
if args.paste and args.file != None:
    print("Error: cannot use paste data and file data at a same time")
    exit()
if args.recursive and args.file == None:
    print("Error: cannot use recursive search when no path is provided")
    exit()
if args.file != None:
    matches = glob.glob(args.file)
    
if args.recursive:
    print("Traversing recursively all matching folders")
    for p in matches:
        if os.path.isfile(p):
            files.append(p)
            #print("Folder " + str(p))
        elif os.path.isdir(p):
            folders.append(p)
    #Search all the found folders
    for fol in folders:
        for r, d, f in os.walk(fol):
            for file in f:
                files.append(os.path.join(r, file))
    #for f in files: print(f)
    print("Found " + str(len(files)) + " to upload")
    #exit()
else:
    for p in matches:
        if os.path.isfile(p):
            p = os.path.abspath(p)
            files.append(p)
            print("Found match " + p)
    #print(files)
    #exit()
    
if not args.paste and len(files) == 0:
    print("No files match")
    exit()
link = ""
#arg = sys.argv[1]
a = args.archive #Get if flag was given
if args.paste:
    
    data = klembord.get(["text/plain", "image/png", "image/jpg", "image/jpeg", "image/gif", "image/svg+xml", "application/octet-stream"])#"image/jpeg"])#, "CF_DSPBITMAP", "CF_BITMAP"])#, "text/plain"])
    sorted_list = [i for i in data.keys()]
    for k in sorted_list:
        if data[k] != None:
            print("There was data at " + k)
        
    print(sorted_list)
    
    png = data['image/png']
    jpg = data['application/octet-stream']
    text = klembord.get_text()
    #print(text)
    if text != None:
        print("You pasted text")
        #print(text)
        text = text.strip(' \t\r\n\0')
        #Encode the text
        text = text.encode('utf-8')
        link = sendToPaste(text, archive = a, contentType=textContentType, data=True)
        print(link)
        
    if png != None and len(png) > 0:
        print("got png image data :3")
        link = sendToPaste(png, archive = a, contentType="image/png", data=True)
        print(link)
    """elif jpg != None and len(jpg) > 0:
        print("got jpg image data :3")
        link = sendToPaste(png, archive = a, contentType="image/jpeg", data=True)
        print(link)"""
        
else:
    links = []
    for f in files:
        link = sendToPaste(f, archive = a)
        links.append(f + '\nin link: ' + link)
        #print(link)
    for link in links:
        print(link)
#klembord.set_text(link)