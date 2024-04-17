import socket

# Service name for the client pod (assuming it's in the same namespace)
SERVICE_NAME = "10.244.189.106"
PORT = 7777
SENT_MESSAGES_FILE = "sent_messages.txt"  # File for client-sent messages
RECEIVED_MESSAGES_FILE = "received_messages.txt"  # File for client-received messages

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
    # Use DNS resolution to connect to the service
    client_socket.connect((socket.gethostbyname(SERVICE_NAME), PORT))

    message = "Hello from the client!"

    # Write sent message to file
    with open(SENT_MESSAGES_FILE, 'a') as message_file:
        message_file.write(f"Sent: {message}\n")

    client_socket.sendall(message.encode())

    data = client_socket.recv(1024)
    print(f"Received: {data.decode()}")

    # Write received message to file
    with open(RECEIVED_MESSAGES_FILE, 'a') as message_file:
        message_file.write(f"Received: {data.decode()}\n")
