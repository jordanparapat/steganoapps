from django.shortcuts import render
from steganoModule import main
    
def index(request):
    return render(request,'index.html')

def encodePage(request):
    if request.method == 'POST':
        global content
        fileNameToProcess = request.POST['uploadedFileName']
        hiddenMessage= request.POST['message']
        uploadedFileName, message, fileLoc = main.encodeFunc(fileNameToProcess, hiddenMessage)
        content = {'uploadedFileName': uploadedFileName, 'message': message, 'fileLoc': fileLoc}
        return render(request, 'result.html', content)
    return render(request, 'encode.html')

def decodePage(request):
    if request.method == 'POST':
        global content
        fileNameToProcess = request.POST['uploadedFileNameToDecode']
        uploadedFileNameToDecode, lsb_hidden_text = main.decodeFunc(fileNameToProcess)
        content = {'uploadedFileNameToDecode': uploadedFileNameToDecode, 'lsb_hidden_text': lsb_hidden_text}
        return render(request, 'resultDecode.html', content)
    return render(request, 'decode.html')

def resultPage(request):
    return render(request,'result.html') 