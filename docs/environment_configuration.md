# 🚀 DEPLOYMENT AND REAL-WORLD SIMULATION GUIDE (MININET & P4)

This document provides a comprehensive guide for deploying a programmable SDN/P4 network, launching realistic DDoS attack scenarios, and evaluating the effectiveness of an AI-assisted DDoS detection and mitigation framework.

---

# STEP 1: ENVIRONMENT SETUP

## System Requirements

* Ubuntu 20.04 LTS
* Minimum RAM: 4 GB
* Minimum Disk Space: 25 GB

## Install the P4 Development Environment

The recommended approach is to use the official P4 automated installation scripts.

```bash
sudo apt update
sudo apt install -y git

git clone https://github.com/p4lang/tutorials.git
cd tutorials/vm-ubuntu-20.04

sudo bash root-dev-bootstrap.sh
cp py3localpath.py ~/
chmod +x ~/py3localpath.py
sudo bash user-dev-bootstrap.sh
```

Installation time typically ranges between 30 and 45 minutes.

### Installed Components

* Mininet
* BMv2 Software Switch
* P4C Compiler
* Scapy
* P4 Runtime Libraries
* Supporting Dependencies

---

# STEP 2: BUILD THE NETWORK TOPOLOGY

## Network Architecture

```text
                           INTERNET ZONE

                h1 (Legitimate User)
                     10.0.0.1
                          |
                          |
                h2 (Botnet Attacker)
                     10.0.0.2
                          |
                          |
                    +------------+
                    | P4 Switch  |
                    |    s1      |
                    +------------+
                     /    |    \
                    /     |     \
                   /      |      \
                  /       |       \
                 /        |        \
                /         |         \
               /          |          \
              /           |           \
             /            |            \
            /             |             \
     h3 (DMZ Server)  h4 (Internal)  h5 (SOC Sensor)
       10.0.0.3         10.0.0.4       10.0.0.5
```

---

## Network Zones

### External Zone

Represents the public Internet.

| Host | Role            |
| ---- | --------------- |
| h1   | Legitimate User |
| h2   | Botnet Attacker |

### DMZ Zone

Public-facing services.

| Host | Role                          |
| ---- | ----------------------------- |
| h3   | Victim Web/Application Server |

### Internal Zone

Trusted enterprise network.

| Host | Role                        |
| ---- | --------------------------- |
| h4   | Internal Client Workstation |

### Monitoring Zone

Security monitoring infrastructure.

| Host | Role             |
| ---- | ---------------- |
| h5   | SOC Sensor / IDS |

---

## Bandwidth Configuration

### Internet Links

```text
h1 → s1 : 100 Mbps
h2 → s1 : 100 Mbps
```

Characteristics:

* High bandwidth
* 5 ms latency

Represents ISP and Internet access.

### Internal Links

```text
h4 → s1 : 20 Mbps
h5 → s1 : 20 Mbps
```

Characteristics:

* Corporate LAN
* 1 ms latency

### Server Link (Bottleneck)

```text
s1 → h3 : 10 Mbps
```

Characteristics:

* Simulates a realistic bottleneck
* Enables congestion under DDoS conditions
* Allows evaluation of mitigation effectiveness

---

# STEP 3: START THE SDN CONTROLLER

Before generating traffic, the controller must be activated.

## Configure Operating Mode

Open:

```bash
sdn_controller.py
```

### Dataset Collection Mode

```python
ENABLE_LOGGING = True
```

Used for collecting real telemetry and generating datasets.

### Protection Testing Mode

```python
ENABLE_LOGGING = False
```

Used when testing the trained AI model.

---

## Launch Controller

```bash
sudo python3 sdn_controller.py
```

The controller performs the following tasks:

* Receives telemetry reports from the P4 switch.
* Executes Random Forest-based attack detection.
* Launches DPI investigation using Scapy.
* Deploys mitigation rules via P4 Runtime.

---

# STEP 4: START THE NETWORK

Launch Mininet:

```bash
sudo python3 network_topo.py
```

Verify connectivity:

```bash
mininet> pingall
```

Open terminals:

```bash
mininet> xterm h1 h2 h3 h4 h5
```

---

# SCENARIO 1: BENIGN TRAFFIC

## Objective

Verify that legitimate traffic is classified correctly without false alarms.

---

## Start Service on the Server

On h3:

```bash
iperf3 -s -p 5001
```

Optional:

```bash
python3 -m http.server 80
```

---

## Generate Legitimate User Traffic

On h1:

```bash
iperf3 -c 10.0.0.3 -p 5001 -t 300
```

```bash
ping 10.0.0.3 -i 0.5
```

---

## Generate Internal Traffic

On h4:

```bash
curl http://10.0.0.3
```

```bash
ping 10.0.0.3
```

---

## Monitor Traffic

On h5:

```bash
tcpdump -i h5-eth0
```

or

```bash
sudo suricata -i h5-eth0
```

---

## Expected Result

Controller output:

```text
Traffic Classification: BENIGN
Attack Probability: ~0%
```

Characteristics:

* Large packet sizes
* Stable TCP sessions
* Low SYN ratio
* No mitigation activated

---

# SCENARIO 2: SYN FLOOD WITH IP SPOOFING

## Objective

Evaluate the complete detection and mitigation pipeline.

---

## Launch Attack

On h2:

```bash
hping3 -S -p 80 --flood --rand-source 10.0.0.3
```

Meaning:

| Parameter     | Description               |
| ------------- | ------------------------- |
| -S            | SYN packets only          |
| -p 80         | Target HTTP service       |
| --flood       | Maximum transmission rate |
| --rand-source | Randomized spoofed IPs    |

---

# WHAT HAPPENS INSIDE THE SYSTEM?

## Second 1 — P4 Switch Telemetry

The switch observes:

* Massive packet volume
* Small packet sizes
* Extremely high SYN ratio

Telemetry reports are sent to the controller.

---

## Second 2 — AI Detection Stage

Random Forest evaluates:

```text
packet_rate
avg_packet_length
syn_ratio
```

Output:

```text
ATTACK DETECTED
Confidence > 95%
```

The controller immediately escalates to investigation mode.

---

## Second 3 — DPI Investigation

Scapy samples approximately:

```text
100 SYN packets
```

Analysis reveals:

```text
99% of packets target 10.0.0.3
```

Controller identifies:

```text
Victim IP = 10.0.0.3
```

---

## Second 4 — Mitigation Stage

Controller installs runtime rules:

```text
Enable Meter
Apply Rate Limiting
Redirect Suspicious Flows
```

Deployment path:

```text
Controller
      ↓
P4 Runtime API
      ↓
P4 Switch
      ↓
Mitigation Activated
```

---

# AVAILABILITY VERIFICATION

While h2 continues the SYN Flood attack:

## Internal User Test

On h4:

```bash
ping 10.0.0.3
```

```bash
curl http://10.0.0.3
```

Expected:

```text
Service remains reachable.
```

---

## External User Test

On h1:

```bash
curl http://10.0.0.3
```

Expected:

```text
Service still responds.
```

Possible effects:

* Slight increase in RTT
* Minor throughput reduction

However:

```text
The server remains operational.
```

---

# SOC VISIBILITY TEST

On h5:

```bash
tcpdump -i h5-eth0
```

or

```bash
suricata -i h5-eth0
```

The SOC analyst can observe:

* Attack initiation
* Traffic surge
* Detection event
* Mitigation deployment
* Traffic normalization

This provides evidence for incident-response evaluation.

---

# PERFORMANCE METRICS

The testbed enables measurement of:

## Detection Metrics

* Accuracy
* Precision
* Recall
* F1-score

## Network Metrics

* Throughput
* Packet Loss
* RTT
* Link Utilization

## Mitigation Metrics

* Time-to-Detect (TTD)
* Time-to-Mitigate (TTM)
* Service Availability

## Security Operations Metrics

* Alert Quality
* Investigation Time
* Telemetry Visibility

---

# CONCLUSION

The system implements a two-stage DDoS defense framework:

```text
Stage 1:
P4 Telemetry
      ↓
Random Forest Detection

Stage 2:
Scapy DPI Investigation
      ↓
Victim Identification
      ↓
P4 Runtime Mitigation
```

Key advantages:

* Real-time DDoS detection.
* Effective against SYN Flood attacks with IP spoofing.
* Preserves service availability through rate limiting.
* Supports SOC monitoring and incident investigation.
* Demonstrates the synergy of P4 programmable data planes, SDN control planes, and AI-based network security.
