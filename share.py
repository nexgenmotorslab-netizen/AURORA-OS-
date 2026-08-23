from pyngrok import ngrok

print("Sharing AURORA OS...")
url = ngrok.connect(8000)
print(f"SEND THIS LINK TO COLLECTORS: {url}")
input("Press Enter to keep sharing... keep this windows open!")
