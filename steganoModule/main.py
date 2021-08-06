from django.core.files.storage import default_storage

import cv2
import docopt
import numpy as np
import re
import string
import os
from PIL import Image
from pathlib import Path
from stegano import lsb

def encodeFunc(uploadedFileName, message):
    class SteganographyException(Exception):
        pass

    class LSB():
        def __init__(self, im):
            self.image = im
            self.height=im.height
            self.width= im.width
            self.nbchannels=5
            self.size = self.width * self.height

            #Mask used to set bits:1->00000001, 2->00000010 ... (using OR gate)
            self.maskONEValues = [1<<0, 1<<1, 1<<2, 1<<3, 1<<4, 1<<5, 1<<6, 1<<7]
            self.maskONE = self.maskONEValues.pop(0) #remove the first value as it is being used

            #Mask used to clear bits: 254->11111110, 253->11111101 ... (using AND gate)
            self.maskZEROValues = [255-(1<<i) for i in range(8)]
            self.maskZERO = self.maskZEROValues.pop(0)

            self.curwidth = 0 #Current width position
            self.curheight = 0 #Current height position
            self.curchan = 0 #Current channel position
            print("Stegano")

        def put_binary_value(self, bits): #to insert bits into the image -- the actual steganography process
            for c in bits:
                val = list(self.image[self.curheight, self.curwidth])
                if int(c) == 1:
                    val[self.curchan] = int(val[self.curchan]) | self.maskONE
                else:
                    val[self.curchan] = int(val[self.curchan]) &self.maskZERO

                #Update image
                self.image[self.curheight, self.curwidth] = tuple(val)

                #Move the pointer to the next space
                self.next_slot()

        def next_slot(self): #to move the pointer to the next location, and error handling if message is too large
            if self.curchan == self.nbchannels-1:
                self.curchan = 0
                if self.curwidth == self.width-1:
                    self.curwidth = 0
                    if self.curheight == self.height-1:
                        self.curheight = 0
                        if self.maskONE == 128:
                            raise SteganographyException("No available slot remaining (image filled)")
                        else:
                            self.maskONE = self.maskONEValues.pop(0)
                            self.maskZERO = self.maskZEROValues.pop(0)
                    else:
                        self.curheight += 1
                else:
                    self.curwidth += 1
            else:
                self.curchan += 1

        def read_bit(self): #to read in a bit from the image, at a certain [height, width][channel]
            val = self.image[self.curheight, self.curwidth][self.curchan]
            val = int(val) & self.maskONE

            #Move pointer to next location after reading in bit
            self.next_slot()

            #Check if corresp bitmask and val have the same set bit
            if val > 0:
                return "1"
            else:
                return "0"

        def read_byte(self):
            return self.read_bits(8)

        def read_bits(self, nb): #to read nb number of bits. returns image binary data and checks if current bit was masked with 1
            bits = ""
            for i in range(nb):
                bits += self.read_bit()
            return bits

        def byteValue(self, val): #to generate the byte value of an int and return it
            return self.binary_value(val, 8)

        def binary_value(self, val, bitsize): #to return the binary value of an int as a byte
            #Extract binary equivalent
            binval = bin(val)[2:]

            #Check if out-of-bounds
            if len(binval)>bitsize:
                raise SteganographyException("Binary value larger than the expected size, catastrophic failure.")

            #Making it 8-bit by prefixing with zeroes
            while len(binval) < bitsize:
                binval = "0"+binval
            return binval

        def encode_text(self, txt):
            l = len(txt)
            binl = self.binary_value(l, 16)
            self.put_binary_value(binl)
            for char in txt:
                c = ord(char)
                self.put_binary_value(self.byteValue(c))
            return self.image

        def decode_text(self):
            ls = self.read_bits(16)
            l = int(ls, 2)
            i = 0
            unhideTxt = ""
            while i < 1:
                tmp = self.read_byte()
                i += 1
                unhideTxt += chr(int(tmp, 2))
            return unhideTxt
        
        def encode_image(self,img, msg):
            length = len(msg)
            if length > 255:
                print("text too long! (don't exeed 255 characters)")
                return False
            encoded = img.copy()
            width, height = img.size
            index = 0
            for row in range(height):
                for col in range(width):
                    if img.mode != 'RGB':
                        r, g, b ,a = img.getpixel((col, row))
                    elif img.mode == 'RGB':
                        r, g, b = img.getpixel((col, row))
                    # first value is length of msg
                    if row == 0 and col == 0 and index < length:
                        asc = length
                    elif index <= length:
                        c = msg[index -1]
                        asc = ord(c)
                    else:
                        asc = b
                    encoded.putpixel((col, row), (r, g , asc))
                    index += 1
            return encoded
        
        def decode_image(self,img):
            width, height = img.size
            msg = ""
            index = 0
            for row in range(height):
                for col in range(width):
                    if img.mode != 'RGB':
                        r, g, b ,a = img.getpixel((col, row))
                    elif img.mode == 'RGB':
                        r, g, b = img.getpixel((col, row))  
                    # first pixel r value is length of message
                    if row == 0 and col == 0:
                        length = b
                    elif index <= length:
                        msg += chr(b)
                    index += 1
            lsb_decoded_image_file = "lsb_" + original_image_file
            #img.save(lsb_decoded_image_file)
            ##print("Decoded image was saved!")
            return msg
        
        def encode_binary(self, data):
            l = len(data)
            if self.width * self.height * self.nbchannels < l+64:
                raise SteganographyException("Carrier image is not big enough to hold all the datas to Steganography")
            self.put_binary_value(self.binary_value(l, 64))
            for byte in data:
                byte = byte if isinstance(byte, int) else ord(byte)
                self.put_binary_value(self.byteValue(byte))
            return self.image
        
        def decode_binary(self):
            l = int(self.read_bits(64), 2)
            output = b""
            for i in range(l):
                output += chr(int(self.read_byte(), 2)).encode("utf-8")

    #driver part:
    #creating new folders:
    if os.path.isdir('steganoModule/static/assets/images/resultEmbed') == False:
        os.makedirs("steganoModule/static/assets/images/resultEmbed")

    gambar_asli = "" #to make the file name global variable
    original_image_file = ""
    lsb_gambar_hasil = ""

    print("The message length is: ",len(message))
    os.chdir("..")
    print("Current Directory Location : "+os.getcwd())
    lsb_img = Image.open("steganoApps/steganoModule/static/assets/images/"+uploadedFileName)
    
    os.chdir("steganoApps/steganoModule/static/assets/images/resultEmbed")
    lsb_img_encoded = LSB(lsb_img).encode_image(lsb_img, message)
    lsb_encoded_image_file = "lsb_" + uploadedFileName
    lsb_img_encoded.save(lsb_encoded_image_file)
    print("Gambar hasil sudah disimpan! Pesan yg disisipkan adalah " + message)
    os.chdir("../../../../..")
    fileLoc = os.getcwd()+"\\"+"steganoModule\static"+"\\"+"assets\images"+"\\"+"resultEmbed"+"\\"+lsb_encoded_image_file

    return uploadedFileName, message, fileLoc

def decodeFunc(uploadedFileNameToDecode):
    class SteganographyException(Exception):
        pass

    class LSB():
        def __init__(self, im):
            self.image = im
            self.height=im.height
            self.width= im.width
            self.nbchannels=5
            self.size = self.width * self.height

            #Mask used to set bits:1->00000001, 2->00000010 ... (using OR gate)
            self.maskONEValues = [1<<0, 1<<1, 1<<2, 1<<3, 1<<4, 1<<5, 1<<6, 1<<7]
            self.maskONE = self.maskONEValues.pop(0) #remove the first value as it is being used

            #Mask used to clear bits: 254->11111110, 253->11111101 ... (using AND gate)
            self.maskZEROValues = [255-(1<<i) for i in range(8)]
            self.maskZERO = self.maskZEROValues.pop(0)

            self.curwidth = 0 #Current width position
            self.curheight = 0 #Current height position
            self.curchan = 0 #Current channel position
            print("Stegano")

        def put_binary_value(self, bits): #to insert bits into the image -- the actual steganography process
            for c in bits:
                val = list(self.image[self.curheight, self.curwidth])
                if int(c) == 1:
                    val[self.curchan] = int(val[self.curchan]) | self.maskONE
                else:
                    val[self.curchan] = int(val[self.curchan]) &self.maskZERO

                #Update image
                self.image[self.curheight, self.curwidth] = tuple(val)

                #Move the pointer to the next space
                self.next_slot()

        def next_slot(self): #to move the pointer to the next location, and error handling if message is too large
            if self.curchan == self.nbchannels-1:
                self.curchan = 0
                if self.curwidth == self.width-1:
                    self.curwidth = 0
                    if self.curheight == self.height-1:
                        self.curheight = 0
                        if self.maskONE == 128:
                            raise SteganographyException("No available slot remaining (image filled)")
                        else:
                            self.maskONE = self.maskONEValues.pop(0)
                            self.maskZERO = self.maskZEROValues.pop(0)
                    else:
                        self.curheight += 1
                else:
                    self.curwidth += 1
            else:
                self.curchan += 1

        def read_bit(self): #to read in a bit from the image, at a certain [height, width][channel]
            val = self.image[self.curheight, self.curwidth][self.curchan]
            val = int(val) & self.maskONE

            #Move pointer to next location after reading in bit
            self.next_slot()

            #Check if corresp bitmask and val have the same set bit
            if val > 0:
                return "1"
            else:
                return "0"

        def read_byte(self):
            return self.read_bits(8)

        def read_bits(self, nb): #to read nb number of bits. returns image binary data and checks if current bit was masked with 1
            bits = ""
            for i in range(nb):
                bits += self.read_bit()
            return bits

        def byteValue(self, val): #to generate the byte value of an int and return it
            return self.binary_value(val, 8)

        def binary_value(self, val, bitsize): #to return the binary value of an int as a byte
            #Extract binary equivalent
            binval = bin(val)[2:]

            #Check if out-of-bounds
            if len(binval)>bitsize:
                raise SteganographyException("Binary value larger than the expected size, catastrophic failure.")

            #Making it 8-bit by prefixing with zeroes
            while len(binval) < bitsize:
                binval = "0"+binval
            return binval

        def decode_text(self):
            ls = self.read_bits(16)
            l = int(ls, 2)
            i = 0
            unhideTxt = ""
            while i < 1:
                tmp = self.read_byte()
                i += 1
                unhideTxt += chr(int(tmp, 2))
            return unhideTxt

        
        def decode_image(self,img):
            width, height = img.size
            msg = ""
            index = 0
            for row in range(height):
                for col in range(width):
                    if img.mode != 'RGB':
                        r, g, b ,a = img.getpixel((col, row))
                    elif img.mode == 'RGB':
                        r, g, b = img.getpixel((col, row))  
                    # first pixel r value is length of message
                    if row == 0 and col == 0:
                        length = b
                    elif index <= length:
                        msg += chr(b)
                    index += 1
            lsb_decoded_image_file = "lsb_" + original_image_file
            #img.save(lsb_decoded_image_file)
            ##print("Decoded image was saved!")
            return msg
        
        def decode_binary(self):
            l = int(self.read_bits(64), 2)
            output = b""
            for i in range(l):
                output += chr(int(self.read_byte(), 2)).encode("utf-8")
            return output


    #driver part:
    #creating new folders:
    gambar_asli = "" #to make the file name global variable
    original_image_file = ""
    lsb_gambar_hasil = ""
    os.chdir("steganoModule/static/assets/images/resultEmbed/")
    lsb_img = Image.open(uploadedFileNameToDecode)
    os.chdir("..") #to go back to the parent directory
    lsb_hidden_text = LSB(lsb_img).decode_image(lsb_img)
    print("Hidden texts were saved as text file!")
    print("Pesannya adalah " + lsb_hidden_text)
    os.chdir("../../../..")
    return uploadedFileNameToDecode, lsb_hidden_text