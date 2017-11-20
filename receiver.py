#python 2.7.12
#!usr/bin/python 

from sys import *
from socket import *
import os 
import random 
import datetime
import pickle 


class receiver: 

	# Constant - packet fields  
	SEQ_NUM = 0;
	ACK_NUM = 1;
	SYN = 2
	ACK = 3
	FIN = 4
	DATA = 5

	def __init__(self, argv): 
		self.receiver_port = int(argv[1]); 
		self.fileName = str(argv[2]); 

		# create socket 
		recvSocket = socket(AF_INET, SOCK_DGRAM); 
		recvSocket.bind(("", self.receiver_port)); 

		# performing 3 way handshake 
		self.handshake(recvSocket); 

		# receiving data / send ack 
		# network termination
		print("Receiving data...");
		self.controlSegment(recvSocket);

		# append additional statistic to log file 



	# Perform 3 way handshake 
	def handshake(self, recvSocket): 
		print("Handshaking"); 
		# waiting for SYN pack 
		# print("Waiting for SYN pack"); 
		packed_SYNSeg, senderAddr = recvSocket.recvfrom(4096); 
		SYNSeg = pickle.loads(packed_SYNSeg);
		recv_time = datetime.datetime.now(); 
		self.log_data('rcv', recv_time, 'S', SYNSeg[self.SEQ_NUM], 0, SYNSeg[self.ACK_NUM]);

		# This if condition should never happen
		# Because we assume 3 way handshake always success here  
		if(SYNSeg[self.SYN] != 1):
			print("Expect: SYN segment"); 
			stdout.flush(); 
			exit(0);  

		# create and send SYNACK segment 
		# print("Sending SYNACK segment"); 
		self.receiverISN = random.randint(2000,2500); 
		SYNACKSeg = [self.receiverISN, SYNSeg[self.SEQ_NUM]+1, 1, 1, 0]
		recvSocket.sendto(pickle.dumps(SYNACKSeg), senderAddr);
		send_time = datetime.datetime.now(); 
		self.log_data('snd', send_time, 'SA', SYNACKSeg[self.SEQ_NUM], 0, SYNACKSeg[self.ACK_NUM]);
 
		# wait for sender ACK - complete handshake 
		packed_ACKSeg, senderAddr = recvSocket.recvfrom(4096); 
		ACKSeg = pickle.loads(packed_ACKSeg); 
		recv_time = datetime.datetime.now(); 
		self.log_data('rcv', recv_time, 'SA', ACKSeg[self.SEQ_NUM], 0, ACKSeg[self.ACK_NUM]);

		# Check if this is an ACK segment 
		# IT MUST BE!!! 
		if(ACKSeg[self.ACK] == 1):
			print("Connection established!!"); 
		else: 
			print("Expected: ACK segment"); 
			print("Unsuccessful handshake"); 
			stdout.flush();
			exit(0); 

		self.nextExpectedSeqNum = ACKSeg[self.SEQ_NUM];
		


	# handle receive data / send ack segment to sender 
	# in-order received data is written to file 
	# out-of-order received data is buffered 
	def controlSegment(self, recvSocket): 
		with open(self.fileName, "wb") as outputFile:

			# start recv data segment from sender 
			packed_dataSeg, senderAddr = recvSocket.recvfrom(4096); 
			dataSeg = pickle.loads(packed_dataSeg); 
			recv_time = datetime.datetime.now();
			self.log_data('rcv', recv_time, 'D', dataSeg[self.SEQ_NUM], 0, dataSeg[self.ACK_NUM]);

			expectedSeqNum = self.nextExpectedSeqNum;

			# buffer contains unorder segment 
			unorder_buffer = []; 

			# continously recv data segment 
			while (dataSeg[self.FIN] == 0): 
				validSeg = True; 

				# if packets arrived are not in order
				# append to unorder_buffer  
				if(dataSeg[self.SEQ_NUM] != expectedSeqNum):
					validSeg = False;
					unorder_buffer.append(dataSeg); 

				# if packet arrive in order 
				# update expected seq number 
				# write valid data segment to output file 
				if(validSeg == True):
					expectedSeqNum += len(dataSeg[self.DATA])
					outputFile.write(dataSeg[self.DATA]); 

					# send ACK 
					dataACKSeg = [dataSeg[self.ACK_NUM], dataSeg[self.ACK_NUM], 0, 1, 0];
					recvSocket.sendto(pickle.dumps(dataACKSeg), senderAddr); 
					send_time = datetime.datetime.now();
					self.log_data('snd', send_time, 'A', dataACKSeg[self.SEQ_NUM], 0, dataACKSeg[self.ACK_NUM]);
 
				packed_dataSeg, senderAddr = recvSocket.recvfrom(4096); 
				dataSeg = pickle.loads(packed_dataSeg); 
			# write last segment to file 
			outputFile.write(dataSeg[self.DATA]);  


		# recv FIN segment 
		# begin network shutdown 
		if(dataSeg[self.FIN] == 1): 
			recv_time = datetime.datetime.now(); 
			self.log_data('rcv', recv_time, 'F', dataSeg[self.SEQ_NUM], 0, dataSeg[self.ACK_NUM]);

			# send FIN ACK segment 
			FASeg = [dataSeg[self.ACK_NUM], dataSeg[self.SEQ_NUM]+1, 0, 1, 1];
			recvSocket.sendto(pickle.dumps(FASeg), senderAddr); 
			send_time = datetime.datetime.now(); 
			self.log_data('snd', send_time, 'FA', FASeg[self.SEQ_NUM], 0, FASeg[self.ACK_NUM]);

			# wait for ACK reply 
			try: 
				packed_finalAckSeg, senderAddr = recvSocket.recvfrom(4096); 
				finalAckSeg = pickle.loads(packed_finalAckSeg); 
				recv_time = datetime.datetime.now(); 
				self.log_data('rcv', recv_time, 'A', finalAckSeg[self.SEQ_NUM], 0, finalAckSeg[self.ACK_NUM]);

			except Exception as err: 
				print("Unsucessful network termination"); 
				stdout.flush(); 
				exit(0);

		print("Connection close");
		recvSocket.close(); 



	# log file function 
	def log(self, text): 
		with open('rcvLog.txt', "a") as logFile:
			logFile.write(text); 

	def log_data(self, action, time, packetType, seq_num, num_bytes, ack_num): 
		self.log(action + ' ; ' + str(time) + ' ; ' + packetType + ' ; ' \
						+ str(seq_num) + ' ; ' + str(num_bytes) + ' ; ' + str(ack_num) + '\n');


# Main function 
def main(argv): 
	receiver(argv); 

main(argv); 