# P4 DATA PLANE IMPLEMENTATION GUIDE (BMV2 SWITCH)

**Project:** Machine-Learning-Enabled DDoS Attacks Detection

**Architecture:** Macroscopic Detection + Deep Packet Inspection (DPI) + Rate Limiting

**Objective:** Aggregate traffic statistics, generate Telemetry reports to the Controller for AI analysis, and enforce Rate Limiting upon attack detection.

---

# OVERALL PIPELINE WORKFLOW

The P4 Switch performs two main parallel tasks:

## Monitoring (Telemetry Generation)

Counts total packets (`tot_pck`), total bytes (`tot_bytes`), and classifies traffic by protocol (`tcp`, `udp`, `syn`).

When a threshold is reached (e.g., 10,000 packets):

1. The Switch clones an existing packet.
2. The clone is modified to use UDP.
3. The Controller IP and UDP port are assigned.
4. A Telemetry report is appended.
5. The clone is sent to the Controller.
6. All counters are reset to 0 for the next monitoring cycle.

## Mitigation (Defense)

The Switch listens for rules pushed by the Controller via the `table_rate_limit` table.

If the Controller identifies a victim IP:

1. A Meter is applied to traffic destined for that IP.
2. If traffic exceeds the configured threshold (RED state), packets are dropped.
3. Otherwise, packets are forwarded normally.

---

# 🛠️ STEP 1: HEADER & METADATA DECLARATION

Define the 16-byte telemetry report structure that exactly matches the Python `DDoSReport` class.

**Notes:**

- No `dst_ip` field is included.
- The Controller identifies the victim using DPI.
- `tot_bytes` must use `bit<32>` to avoid overflow.

### Telemetry Report Structure

```p4
// 1. Telemetry Report Structure (16 Bytes)
// Matches Python scapy_headers.py exactly

header telemetry_report_t {
    bit<32> switch_id;    // 4 Bytes
    bit<16> tot_pck;      // 2 Bytes (Total Packets)
    bit<32> tot_bytes;    // 4 Bytes (Total Bytes)
    bit<16> tcp_pck;      // 2 Bytes
    bit<16> udp_pck;      // 2 Bytes
    bit<16> syn_pck;      // 2 Bytes
    // Total: 16 Bytes
}
```

### Extend Main Header Structure

```p4
// 2. Extend Main Headers Structure

struct headers {
    ethernet_t           ethernet;
    ipv4_t               ipv4;
    tcp_t                tcp;
    udp_t                udp;
    telemetry_report_t   telemetry;
}
```

### Metadata Declaration

```p4
// 3. Internal Metadata

struct metadata {
    bit<16> counter_tot;
    bit<32> tot_bytes;

    bit<16> counter_tcp;
    bit<16> counter_udp;
    bit<16> counter_syn;

    bit<32> meter_color;
}
```

---

# 🛠️ STEP 2: STATEFUL MEMORY (REGISTERS & METER)

Because P4 forgets variables after a packet leaves the pipeline, Registers are required to maintain statistics over time.

### Global Counters

```p4
// 1. Global Counters

register<bit<16>>(1) reg_tot_pck;
register<bit<32>>(1) reg_tot_bytes;

register<bit<16>>(1) reg_tcp_pck;
register<bit<16>>(1) reg_udp_pck;
register<bit<16>>(1) reg_syn_pck;
```

### Rate Limiter

```p4
// 2. Rate Limiter

meter(1024, MeterType.packets) meter_syn_flood;
```

---

# 🛠️ STEP 3: INGRESS PIPELINE (COUNTING & MITIGATION)

The ingress pipeline:

- Updates counters.
- Executes mitigation rules.
- Triggers telemetry generation.

### Ingress Control

```p4
control MyIngress(
    inout headers hdr,
    inout metadata meta,
    inout standard_metadata_t standard_metadata
) {

    // ACTION 1: Rate Limiting

    action action_set_meter_index(bit<32> meter_idx) {

        meter_syn_flood.execute_meter(
            meter_idx,
            meta.meter_color
        );

        if (meta.meter_color == 2) {
            mark_to_drop(standard_metadata);
        }
    }

    // TABLE: Rate Limiting Table

    table table_rate_limit {

        key = {
            hdr.ipv4.dstAddr : exact;
        }

        actions = {
            action_set_meter_index;
            NoAction;
        }

        size = 1024;
    }

    // ACTION 2: Counter Update

    action update_counters() {

        bit<16> cur_tot_pck;
        bit<32> cur_tot_bytes;

        reg_tot_pck.read(cur_tot_pck, 0);
        reg_tot_bytes.read(cur_tot_bytes, 0);

        meta.counter_tot = cur_tot_pck + 1;

        meta.tot_bytes =
            cur_tot_bytes +
            (bit<32>)standard_metadata.packet_length;

        reg_tot_pck.write(0, meta.counter_tot);
        reg_tot_bytes.write(0, meta.tot_bytes);

        // Similar logic required for:
        // TCP packets
        // UDP packets
        // SYN packets
    }

    apply {

        if (hdr.ipv4.isValid()) {

            // 1. Mitigation

            table_rate_limit.apply();

            // 2. Monitoring

            update_counters();

            // 3. Telemetry Trigger

            if (meta.counter_tot == 10000) {

                clone3(
                    CloneType.I2E,
                    255,
                    0
                );
            }
        }
    }
}
```

---

# 🛠️ STEP 4: EGRESS PIPELINE (CLONE MUTATION & RESET)

The original packet continues to its destination.

The cloned packet is converted into a telemetry report and sent to the Controller.

### Egress Control

```p4
control MyEgress(
    inout headers hdr,
    inout metadata meta,
    inout standard_metadata_t standard_metadata
) {

    action mutate_to_telemetry_udp() {

        // 1. Modify IPv4 Header

        hdr.ipv4.protocol = 17;

        // Update to your Controller IP

        hdr.ipv4.dstAddr =
            32w0x0A000064;

        // 2. Build UDP Header

        hdr.udp.setValid();

        hdr.udp.srcPort = 12345;
        hdr.udp.dstPort = 50000;

        // 3. Attach Telemetry Header

        hdr.telemetry.setValid();

        hdr.telemetry.switch_id = 1;

        hdr.telemetry.tot_pck =
            meta.counter_tot;

        hdr.telemetry.tot_bytes =
            meta.tot_bytes;

        hdr.telemetry.tcp_pck =
            meta.counter_tcp;

        hdr.telemetry.udp_pck =
            meta.counter_udp;

        hdr.telemetry.syn_pck =
            meta.counter_syn;
    }

    action reset_all_registers() {

        reg_tot_pck.write(0, 0);
        reg_tot_bytes.write(0, 0);

        reg_tcp_pck.write(0, 0);
        reg_udp_pck.write(0, 0);
        reg_syn_pck.write(0, 0);
    }

    apply {

        if (standard_metadata.instance_type == 1) {

            mutate_to_telemetry_udp();

            reset_all_registers();
        }
    }
}
```

---

# ⚠️ CRITICAL CHECKLIST FOR P4 DEVELOPER

Before compiling and integrating with the Python Controller, verify:

- [ ] Table Name = `table_rate_limit`
- [ ] Action Name = `action_set_meter_index`
- [ ] Meter Name = `meter_syn_flood`
- [ ] UDP Destination Port = `50000`
- [ ] Controller IP correctly configured in `hdr.ipv4.dstAddr`
- [ ] Telemetry structure exactly matches Python `DDoSReport`

### Controller IP Example

```p4
hdr.ipv4.dstAddr = 32w0x0A000064;
```

### Controller Startup

```bash
python3 sdn_controller.py
```

---

# EXPECTED RESULT

The completed P4 switch should:

- Aggregate macroscopic traffic statistics.
- Generate telemetry reports.
- Send reports to the SDN Controller.
- Support Random Forest attack detection.
- Support DPI-based victim identification.
- Receive mitigation commands.
- Apply Meter-based rate limiting.
- Preserve service availability during DDoS attacks.