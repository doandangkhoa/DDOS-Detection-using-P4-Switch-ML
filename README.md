🛡️ SDN-P4 ML-Driven DDoS Mitigation System

Co-Authors: Doan Dang Khoa (Calvin Doan) | Nguyen Huu Long

Institution: Hanoi University of Science and Technology (HUST)

📌 Project Overview

This project presents an End-to-End Closed-Loop Security System designed to detect and mitigate Distributed Denial of Service (DDoS) attacks—particularly TCP SYN Floods—in real time.

Unlike traditional security architectures that rely heavily on edge firewalls, this system shifts the first layer of detection into the programmable data plane, leveraging:

Software Defined Networking (SDN)
P4 Programmable Switches (BMv2)
Machine Learning (Random Forest)
Deep Packet Inspection (DPI)

The architecture enables:

Real-time telemetry collection
Low-latency attack detection
Accurate victim identification
Automated mitigation through SDN control
🏗️ System Architecture
Enterprise Network Topology
                        INTERNET ZONE
                 ┌────────────────────────┐
                 │                        │
                 │   h1 (Legitimate User) │
                 │   h2 (Botnet Attacker) │
                 └────────────┬───────────┘
                              │
                              │ 100 Mbps
                              │
                    ┌───────────────────┐
                    │   P4 SWITCH s1    │
                    │      (BMv2)       │
                    └───────┬─────┬─────┘
                            │     │
                            │     │
                  10 Mbps   │     │ 20 Mbps
               (Bottleneck) │     │
                            │     │
                            ▼     ▼

                    h3 (DMZ Server)
                    Victim Target

                    h4 (Internal LAN)
                    Employee Workstation

                    h5 (SOC / IDS Sensor)
                    Traffic Monitoring
🔄 Closed-Loop Security Workflow
Traffic
    │
    ▼
P4 Switch (Telemetry Generation)
    │
    ▼
SDN Controller
    │
    ▼
Random Forest Detection
    │
    ▼
Attack Detected
    │
    ▼
Deep Packet Inspection (Scapy)
    │
    ▼
Victim Identification
    │
    ▼
P4 Runtime API
    │
    ▼
Rate Limiting Activated
    │
    ▼
Service Availability Preserved
📡 Data Plane (P4 Switch - BMv2)

The P4 switch acts as the first line of defense and telemetry sensor.

Responsibilities:

Aggregate traffic statistics in real time.
Count:
Total packets (tot_pck)
Total bytes (tot_bytes)
TCP packets (tcp_pck)
UDP packets (udp_pck)
SYN packets (syn_pck)
Generate lightweight telemetry reports.
Send telemetry reports to the SDN Controller.
Enforce rate-limiting rules during mitigation.

Telemetry reports are encapsulated inside UDP packets and periodically transmitted to the Controller.

🧠 Control Plane (SDN Controller)

The Controller is implemented as a multi-threaded Python application.

File:

control_plane/sdn_controller.py

Responsibilities:

Receive telemetry reports from the P4 switch.
Extract traffic features.
Execute machine-learning inference.
Trigger DPI investigations when attacks are suspected.
Identify victim hosts.
Push mitigation rules into the P4 switch.
🤖 Intelligence Layer (Machine Learning)

The system employs a Random Forest Classifier trained on synthetic enterprise traffic.

Input Features
Average Packet Length
Packet Rate
TCP Ratio
UDP Ratio
SYN Ratio
Classification Targets
0 → Benign
1 → DDoS Attack
Advantages
High detection accuracy
Low computational overhead
Reduced false positives
Robust against Flash Crowds and P2P traffic
⚙️ Environment Setup
Requirements
Component	Requirement
OS	Ubuntu 20.04 LTS
RAM	≥ 4 GB
Disk	≥ 25 GB
Python	≥ 3.8
1. Install Mininet, BMv2 and P4C
sudo apt update
sudo apt install -y git

git clone https://github.com/p4lang/tutorials.git

cd tutorials/vm-ubuntu-20.04

sudo ./root-bootstrap.sh

sudo su p4 -c "./user-bootstrap.sh"
2. Set Up Python Environment
python3 -m venv venv

source venv/bin/activate

pip install -r requirements.txt

sudo setcap cap_net_raw,cap_net_admin=eip \
$(realpath venv/bin/python3)
🚀 Running the Simulation
Step 1: Start the Enterprise Topology
sudo python3 topology/network_topo.py

Verify connectivity:

mininet> pingall

Open terminal windows:

mininet> xterm h1 h2 h3 h4 h5
Step 2: Launch the Controller

Open a new terminal:

source venv/bin/activate

python3 control_plane/sdn_controller.py

Expected output:

[INFO] Controller Started
[INFO] Waiting for Telemetry Reports...
🧪 Scenario 1: Benign Traffic
Start Service on h3
iperf3 -s -p 5001
Generate Legitimate Traffic from h1
iperf3 -c 10.0.0.3 -p 5001 -t 300

Optional ICMP traffic:

ping 10.0.0.3 -i 0.5
Expected Result
Classification: BENIGN
Attack Probability: ~0%

Characteristics:

Large packets
Stable TCP sessions
Low SYN ratio
Normal bandwidth usage
⚠️ Scenario 2: SYN Flood Attack
Launch Attack from h2
hping3 -S -p 80 --flood --rand-source 10.0.0.3
Parameter Explanation
Parameter	Description
-S	Send SYN packets
-p 80	Target TCP port 80
--flood	Maximum transmission speed
--rand-source	Spoof source IP addresses
🔍 Attack Detection Process
Stage 1 — Telemetry Collection

The P4 switch observes:

High Packet Rate
High SYN Ratio
Small Packet Sizes

Telemetry is sent to the Controller.

Stage 2 — AI-Based Detection

Random Forest evaluates:

avg_length ↓↓↓
packet_rate ↑↑↑
syn_ratio ↑↑↑

Result:

ATTACK DETECTED
Confidence > 95%
Stage 3 — DPI Investigation

Scapy captures recent packets:

sniff()

Analysis reveals:

Destination IP:
10.0.0.3

Victim identified:

Victim = h3
Stage 4 — Automated Mitigation

Controller pushes mitigation rules:

table_add table_rate_limit \
action_set_meter_index \
10.0.0.3 => 1

The switch activates:

meter_syn_flood

Excessive packets are dropped.

Legitimate traffic remains forwarded.

✅ Availability Verification

While the attack is ongoing:

From h1:

ping 10.0.0.3

Expected result:

64 bytes from 10.0.0.3
64 bytes from 10.0.0.3
64 bytes from 10.0.0.3

Possible effects:

Slightly higher latency
Occasional delays

However:

Service remains available.
🎯 Key Contributions
Programmable Data Plane Monitoring using P4.
Machine-Learning-Based DDoS Detection.
Deep Packet Inspection for Victim Identification.
Automated SDN Mitigation Workflow.
Real-Time Rate Limiting.
Support for IP-Spoofed SYN Flood Attacks.
Preservation of Service Availability.
📖 Future Work

Potential improvements include:

Multi-class attack classification.
XGBoost and LightGBM integration.
INT (In-band Network Telemetry).
eBPF-based DPI.
Suricata/Zeek integration.
Distributed SDN Controllers.
Hardware deployment on Tofino switches.
📜 License

This project is intended for academic research and educational purposes.

© Hanoi University of Science and Technology (HUST)