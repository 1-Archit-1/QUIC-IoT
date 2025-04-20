from client_files import IMUClient, IMUClientSingleStream, IMUClientNoPriority,IMUClientNoPriorityV2
import argparse
import asyncio
SERVER = "172.190.228.31"

if __name__ == '__main__':
    argparse = argparse.ArgumentParser(description="QUIC Client for IMU Data")
    argparse.add_argument('--host', type=str, help='Host to connect to: local,server')
    argparse.add_argument('--stream', type=str, help='Stream type: single, multi, no_priority')
    #get args 
    args = argparse.parse_args()
    if args.host == 'local':
        host= 'localhost'
    else:
        host = SERVER
    if args.stream == 'single':
        client = IMUClientSingleStream()
    elif args.stream == 'multi':
        client = IMUClient()
    elif args.stream == 'no_priority':
        client = IMUClientNoPriority()
    print(client)
    asyncio.run(client.start(host))