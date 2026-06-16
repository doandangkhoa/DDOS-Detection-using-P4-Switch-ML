
# 🌐 Enhanced SDN/P4 DDoS Defense Testbed Topology

This topology is designed to simulate a more realistic enterprise network environment for evaluating AI-assisted DDoS detection and mitigation using P4 programmable switches and an SDN controller.

---

# 1. Network Architecture

```text
                            INTERNET ZONE

                  h1 (Legitimate User)
                       10.0.0.1
                            |
                            |
                            |
                  h2 (Botnet Attacker)
                       10.0.0.2
                            |
                            |
                            |
                     +---------------+
                     |   P4 Switch   |
                     |      s1       |
                     +---------------+
                      |      |      |
                      |      |      |
                      |      |      |
                      |      |      |
                      |      |      +-------------------+
                      |      |                          |
                      |      |                          |
                      |      |                    h5 (SOC Sensor)
                      |      |                     10.0.0.5
                      |      |
                      |      |
                      |      +-------------------+
                      |                          |
                      |                          |
                      |                    h4 (Internal Client)
                      |                     10.0.0.4
                      |
                      |
                      |
                h3 (DMZ Web Server)
                   10.0.0.3

                           DATACENTER / DMZ
```

---

# 2. Security Zones

## 🌍 External Zone (Internet)

Contains external entities interacting with the organization.

| Host | Role |
|--------|--------|
| h1 | Legitimate User |
| h2 | Botnet / Attacker |

---

## 🏢 DMZ Zone

Contains publicly exposed services.

| Host | Role |
|--------|--------|
| h3 | Victim Web Server |

Example services:

```bash
iperf3 -s -p 5001
python3 -m http.server 80
```

---

## 🖥 Internal Zone

Contains trusted internal assets.

| Host | Role |
|--------|--------|
| h4 | Internal Employee Workstation |

Purpose:

- Verify business continuity during attacks
- Test service availability after mitigation

---

## 🔍 Monitoring Zone

Contains monitoring and security tools.

| Host | Role |
|--------|--------|
| h5 | SOC Sensor / IDS |

Possible tools:

```bash
tcpdump
suricata
zeek
wireshark
```

---

# 3. Bandwidth Design

The topology intentionally creates a bottleneck.

## Internet Links

```text
h1 → s1 : 100 Mbps
h2 → s1 : 100 Mbps
```

Configured using:

```python
bw=100
delay='5ms'
```

Represents:

- ISP connection
- Public Internet

---

## Internal Links

```text
h4 → s1 : 20 Mbps
h5 → s1 : 20 Mbps
```

Configured using:

```python
bw=20
delay='1ms'
```

Represents:

- Corporate LAN

---

## Server Link (Bottleneck)

```text
s1 → h3 : 10 Mbps
```

Configured using:

```python
bw=10
delay='1ms'
```

Purpose:

- Simulate realistic service saturation
- Demonstrate congestion during DDoS

---

# 4. Expected Traffic Flow

## Normal Operation

```text
h1
 ↓
P4 Switch
 ↓
h3
```

Traffic examples:

```bash
iperf3
HTTP
ICMP
```

Controller should classify:

```text
BENIGN
```

---

# 5. DDoS Scenario

## Attack Generation

From h2:

```bash
hping3 -S -p 80 --flood --rand-source 10.0.0.3
```

Attack path:

```text
h2
 ↓ 100 Mbps
P4 Switch
 ↓ 10 Mbps
h3
```

Result:

```text
Queue Build-up
↓
Packet Loss
↓
Server Saturation
```

---

# 6. AI Detection Workflow

## Stage 1: Telemetry Collection

P4 Switch exports:

```text
packet_count
byte_count
avg_packet_length
syn_ratio
flow_count
```

to:

```text
UDP 50000
```

toward:

```text
SDN Controller
```

---

## Stage 2: Machine Learning Detection

Random Forest evaluates:

```text
avg_length
packet_rate
syn_ratio
```

Example result:

```text
Attack Probability = 98%
```

---

## Stage 3: DPI Investigation

Scapy samples packets:

```python
sniff(count=100)
```

Result:

```text
Victim = 10.0.0.3
```

---

## Stage 4: Mitigation

Controller installs:

```text
Meter Rules
Rate Limiting
```

via:

```text
P4 Runtime API
```

---

# 7. Availability Validation

While h2 performs SYN Flood:

### Internal user

```bash
h4 ping 10.0.0.3
```

### External user

```bash
h1 curl http://10.0.0.3
```

Expected result:

```text
Service remains reachable.
```

Although:

```text
Latency increases slightly.
```

This demonstrates:

```text
Availability Preservation
```

instead of:

```text
Complete Traffic Blocking
```

---

# 8. SOC Monitoring Scenario

On h5:

```bash
tcpdump -i h5-eth0
```

or

```bash
suricata -i h5-eth0
```

The SOC analyst can observe:

- Attack start time
- Packet rate
- Mitigation activation
- Traffic reduction after meter deployment

This provides evidence for:

- Detection accuracy
- Response time
- Mitigation effectiveness

---

# 9. Experimental Objectives

The topology allows evaluation of:

### Detection Performance

- Accuracy
- Precision
- Recall
- F1-score

### Network Performance

- Throughput
- Packet Loss
- RTT
- Link Utilization

### Mitigation Performance

- Time-to-Detect
- Time-to-Mitigate
- Remaining Service Availability

### SOC Visibility

- Telemetry Quality
- Alert Correlation
- Incident Investigation

---

# 10. Why This Topology Is Better

Compared with the basic 3-host topology, this enhanced topology provides:

✅ Realistic bandwidth bottleneck

✅ Legitimate and malicious traffic simultaneously

✅ Internal business user validation

✅ Dedicated monitoring/SOC node

✅ Better demonstration of rate limiting

✅ Suitable for thesis, research, and SOC-lab projects

✅ Closer to real enterprise network architecture
