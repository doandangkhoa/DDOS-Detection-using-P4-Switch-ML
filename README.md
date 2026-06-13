# 🛡️ SDN-P4 ML-Driven DDoS Mitigation System

**Co-Author:** Doan Dang Khoa (Calvin Doan)  | Nguyen Huu Long
**Institution:** Hanoi University of Science and Technology (HUST)

---

## 📌 Project Overview
This project introduces an **End-to-End Closed-Loop Security System** designed to detect and mitigate Distributed Denial of Service (DDoS) attacks—specifically SYN Floods—in real-time. 

By shifting the defense mechanism from traditional edge firewalls to the programmable data plane, this system leverages **Software-Defined Networking (SDN)**, **P4 Programmable Switches (BMv2)**, and **Machine Learning (Random Forest)** to achieve high-accuracy threat detection with minimal processing latency.

## 🏗️ System Architecture
The architecture operates across three distinct layers:

1. **The Data Plane (P4 Switch - BMv2):**
   * Acts as the first line of defense and the primary telemetry sensor.
   * Utilizes a custom P4 program to perform **Time-Window Aggregation**, counting packets (`tot_pck`, `tcp_pck`, `udp_pck`, `syn_pck`) directly at the hardware/ASIC level.
   * Periodically encapsulates these counters into a lightweight, custom 16-byte UDP Telemetry Report and forwards it to the controller.

2. **The Control Plane (SDN Controller):**
   * A multi-threaded Python application (`sdn_controller.py`) listening on UDP port 50000.
   * Parses incoming telemetry using custom Scapy headers and feeds it into the AI engine.
   * Capable of automatically generating labeled ground-truth datasets for model retraining.

3. **The Intelligence Layer (Machine Learning):**
   * Employs a **Random Forest Classifier** trained on highly realistic synthetic network data.
   * Robust against evasion techniques: specifically trained to distinguish malicious traffic from benign anomalies like **Flash Crowds** and P2P traffic, minimizing False Positives.
   * Once an attack is confirmed, it triggers mitigation commands via `simple_switch_CLI` (Thrift) to push strict Rate-Limiting rules (Meters) down to the P4 Switch, instantly throttling the attacker's bandwidth.

---
