#python 2.7.12
#!usr/bin/python 

from sys import *
from socket import *
import os 
import random 
import datetime
import pickle 


class sender: 

	# Constant - packet fields 
	SEQ_NUM = 0;
	ACK_NUM = 1;
	SYN = 2
	ACK = 3
	FIN = 4
	DATA = 5

	def __init__(self, argv): 

		# input 
		self.receiver_ip = str(argv[1]); 
		self.receiver_port = int(argv[2]); 
		self.fileName = str(argv[3]); 
		self.MWS = int(argv[4]); 
		self.MSS = int(argv[5]);
		self.timeout = int(argv[6]); 
		self.pdrop = float(argv[7]); 
		self.seed = int(argv[8]); 

		# statistic variables 
		self.segCount = 0; 
		self.byteCount = 0; 
		self.retransmitCount = 0; 
		self.dropSegCount = 0; 
		self.dupAckCount = 0; 

		# create UDP socket 
		senderSocket = socket(AF_INET, SOCK_DGRAM);
 
		# perform three way handshake 
		self.handshake(senderSocket); 

		# initialise buffer contains STP_segment to be sent 
		try: 
			self.readFile(); 
		except: 
			print(self.fileName + 'NOT FOUND'); 
			stdout.flush(); 
			exit(0);

		# transmitting data and receiving ACK 
		# terminate connection 
		random.seed(self.seed); 

		print("Transmitting data ....");
		self.startTime = datetime.datetime.now();
		counter = 0;  
		while(counter < len(self.toSend_buffer)): 
			currUnpackedSeg = self.toSend_buffer[self.segCount]; 
			self.socketHandle(currUnpackedSeg, senderSocket); 
			counter += 1;

		# Append additional statistic to log file after completion 
		with open('snderLog.txt', "a") as summary: 
			summary.write("Amount of data transferred: " + str(self.byteCount) +'\n'); 
			summary.write("Number of packets sent: " + str(self.segCount) +'\n'); 
			summary.write("Number of packets dropped: " + str(self.dropSegCount) +'\n'); 
			summary.write("Number of retransmitted segment: " + str(self.retransmitCount) +'\n');
			summary.write("Number of duplicate ACK segment: " + str(self.dupAckCount) +'\n');

	# perform 3 way handshake 
	# packet contains no payload 
	def handshake(self, senderSocket):
		print("Handshaking");
		# create and send SYN segment  
		# print("Sending SYN segment"); 
		self.senderISN = random.randint(100, 500);  
		SYNseg = [self.senderISN, 0, 1, 0, 0];
		senderSocket.sendto(pickle.dumps(SYNseg), (self.receiver_ip, self.receiver_port)); 
		send_time = datetime.datetime.now(); 
		self.log_data('snd ', send_time, 'S', SYNseg[self.SEQ_NUM], 0, SYNseg[self.ACK_NUM]);


		# wait for SYNACK segment 
		packed_SYNACKseg, recvAddr = senderSocket.recvfrom(4096); 
		SYNACKseg = pickle.loads(packed_SYNACKseg);
		recv_time = datetime.datetime.now() 
		self.log_data('rcv ', recv_time, 'SA', SYNACKseg[self.SEQ_NUM], 0, SYNACKseg[self.ACK_NUM]);


		# test if it is SYNACK segment 
		if(SYNACKseg[self.SYN] == 1 and SYNACKseg[self.ACK] == 1):
			 # create and send ACK segment 
			ackSeg = [self.senderISN+1, SYNACKseg[self.SEQ_NUM]+1, 0, 1, 0];
			senderSocket.sendto(pickle.dumps(ackSeg),(self.receiver_ip, self.receiver_port));
			send_time = datetime.datetime.now(); 
			self.log_data('snd ', send_time, 'A', self.senderISN+1, 0, SYNACKseg[self.SEQ_NUM]+1);

		else: 
			print("Expected SYNACK segment");
			stdout.flush(); 
			exit(0); 

		print("Connection Established!!"); 
		


	# create a toSend_buffer contains STP_segment ready to be sent through socket 
	def readFile(self): 
		self.toSend_buffer = []; 
		with open(self.fileName, "rb") as myFile: 
			# first data segment 
			currChunk = myFile.read(self.MSS); 
			seqNum = self.senderISN + 1;   
			expectAckNum = seqNum + len(currChunk); 

			# when reach EOF, read() contains empty string 
			while(currChunk != ''): 
				prevChunk = currChunk; 
				currChunk = myFile.read(self.MSS); 

				# is not last segment 
				if(len(currChunk) != 0): 
					# SYN = 0, ACK = 1, FIN = 0 
					dataSeg = [seqNum, expectAckNum, 0, 1, 0]; 
					dataSeg.append(prevChunk); 		# attach data to header 
					self.toSend_buffer.append(dataSeg); 

				# last segment is reached 
				# start initiating four-segment network termination 
				else: 
					# SYN = 0, ACK = 1, FIN = 1 
					dataSeg = [seqNum, expectAckNum, 0, 1, 1]; 
					dataSeg.append(prevChunk); 		# attach data to header 
					self.toSend_buffer.append(dataSeg); 

				seqNum += len(prevChunk); 
				expectAckNum = seqNum + len(currChunk); 

			# number of byte sent for statistic 
			self.byteCount += seqNum; 


	# handle sending data segment and receiving ack if FIN == 0 
	# terminate network connection if FIN == 1 
	def socketHandle(self, segment, senderSocket): 
		if(segment[self.FIN] == 0):
			packed_segment = pickle.dumps(segment); 

			# variables for fast retransmission 
			sendBase = self.senderISN+1; 
			dupAckCounter = 0; 

			# PLD Module - packet lost simulation 
			# data sent event 
			num = random.random(); 
			if(num > self.pdrop): 
				# print("Packet Transmit"); 
				senderSocket.sendto(packed_segment, (self.receiver_ip, self.receiver_port)); 
				send_time = datetime.datetime.now(); 
				self.log_data('snd ', send_time, 'D', segment[self.SEQ_NUM], len(segment[self.DATA]), segment[self.ACK_NUM]);
				self.segCount += 1; 
			else: 
				# print("Packet Dropped"); 
				send_time = datetime.datetime.now();
				self.log_data('drop', send_time, 'D', segment[self.SEQ_NUM], len(segment[self.DATA]), segment[self.ACK_NUM]);
				self.dropSegCount += 1; 
 
			# ACK received event 
			try: 
				senderSocket.settimeout(self.timeout); 
				dataAckSeg, recvAddr = senderSocket.recvfrom(4096); 
				unpacked_dataAckSeg = pickle.loads(dataAckSeg); 
				recv_time = datetime.datetime.now();
				self.log_data('rcv ', recv_time, 'A', unpacked_dataAckSeg[self.SEQ_NUM], 0, unpacked_dataAckSeg[self.ACK_NUM]);

				if(unpacked_dataAckSeg[self.ACK_NUM] > sendBase):
					sendBase = segment[self.ACK_NUM]; 
					#This model does not support Window Size 
					#Thus there will be no unacknowledged segment on sender side 
				#duplicate ACK
				else: 
					self.dupAckCount += 1; 	# this is for logging 
					dupAckCounter += 1; 
					if(dupAckCounter == 3): 
						# STP fast retransmission
						self.retransmitCount += 1; 
						self.socketHandle(segment, senderSocket); 
			# timeout - retransmit event  
			except timeout: 
				self.retransmitCount += 1; 
				self.socketHandle(segment, senderSocket);

		# network termination 
		else:
			packed_segment = pickle.dumps(segment); 
			senderSocket.sendto(packed_segment, (self.receiver_ip, self.receiver_port)); 
			send_time = datetime.datetime.now(); 
			self.log_data('snd ', send_time, 'F', segment[self.SEQ_NUM], 0, segment[self.ACK_NUM]);

			# waiting for FA segement
			# assume no packet loss at this stage 
			senderSocket.settimeout(self.timeout); 
			packed_FASeg, recvAddr = senderSocket.recvfrom(4096); 
			FASeg = pickle.loads(packed_FASeg); 
			recv_time = datetime.datetime.now();
			self.log_data('rcv ', recv_time, 'FA', FASeg[self.SEQ_NUM], 0, FASeg[self.ACK_NUM]);

			if(FASeg[self.ACK] == 1 and FASeg[self.FIN] == 1):
				# send ACK segment 
				ACKSeg = [FASeg[self.ACK_NUM], FASeg[self.SEQ_NUM]+1, 0, 1, 0]; 
				senderSocket.sendto(pickle.dumps(ACKSeg), (self.receiver_ip, self.receiver_port));
				send_time = datetime.datetime.now(); 
				self.log_data('snd ', send_time, 'A', FASeg[self.SEQ_NUM], 0, FASeg[self.ACK_NUM]);
			else:
				print("Incorrect FA segment"); 
				stdout.flush()
				exit(0); 

			senderSocket.close(); 
			print("Connection close");
	

	# log file function 
	def log(self, text): 
		with open('snderLog.txt', "a") as logFile:
			logFile.write(text); 

	def log_data(self, action, time, packetType, seq_num, num_bytes, ack_num): 
		self.log(action + ' ; ' + str(time) + ' ; ' + packetType + ' ; ' \
						+ str(seq_num) + ' ; ' + str(num_bytes) + ' ; ' + str(ack_num) + '\n');

# main 
def main(argv): 
	sender(argv); 

main(argv); 