#include <core.p4>
#include <v1model.p4>
#include "includes/headers.p4"

control MyIngress(inout headers hdr, inout metadata meta, inout standard_metadata_t standard_metadata) {
    
    // 1. KHAI BÁO BIẾN TRẠNG THÁI (REGISTERS & METERS)
    register<bit<16>>(1) reg_tot_pck;
    register<bit<32>>(1) reg_tot_bytes;
    register<bit<16>>(1) reg_tcp_pck;
    register<bit<16>>(1) reg_udp_pck;
    register<bit<16>>(1) reg_syn_pck;

    meter(1024, MeterType.bytes) meter_syn_flood;

    // 2. KHAI BÁO ACTIONS
    action set_egress_port(bit<9> port) { 
        standard_metadata.egress_spec = port; 
    }
    
    action Drop() { 
        mark_to_drop(standard_metadata); 
    }
    
    action action_set_meter_index(bit<32> idx) {
        meter_syn_flood.execute_meter((bit<32>)idx, meta.meter_color);
    }

    // 3. KHAI BÁO TABLES
    table ipv4_lpm {
        key = { hdr.ipv4.dstAddr: lpm; }
        actions = { set_egress_port; Drop; NoAction; }
        size = 1024;
        default_action = NoAction();
    }

    table table_rate_limit {
        key = { hdr.ipv4.dstAddr: exact; }
        actions = { action_set_meter_index; NoAction; }
        size = 1024;
        default_action = NoAction();
    }

    // 4. LOGIC THỰC THI CHÍNH
    apply {
        if (hdr.ipv4.isValid()) {
            meta.meter_color = 0;
            
            ipv4_lpm.apply();
            table_rate_limit.apply();
            
            if (meta.meter_color == 2) { 
                mark_to_drop(standard_metadata);
            }

            bit<16> t_pck; bit<32> t_bytes; bit<16> t_tcp; bit<16> t_udp; bit<16> t_syn;

            reg_tot_pck.read(t_pck, 0);
            reg_tot_bytes.read(t_bytes, 0);
            reg_tcp_pck.read(t_tcp, 0);
            reg_udp_pck.read(t_udp, 0);
            reg_syn_pck.read(t_syn, 0);

            t_pck = t_pck + 1;
            t_bytes = t_bytes + (bit<32>)hdr.ipv4.totalLen;

            if (hdr.tcp.isValid()) {
                t_tcp = t_tcp + 1;
                if ((hdr.tcp.ctrl & 0x02) == 0x02) { 
                    t_syn = t_syn + 1;
                }
            } else if (hdr.udp.isValid()) {
                t_udp = t_udp + 1;
            }

            reg_tot_pck.write(0, t_pck);
            reg_tot_bytes.write(0, t_bytes);
            reg_tcp_pck.write(0, t_tcp);
            reg_udp_pck.write(0, t_udp);
            reg_syn_pck.write(0, t_syn);

            if (t_pck >= 100) { 
                meta.tot_pck   = t_pck;
                meta.tot_bytes = t_bytes;
                meta.tcp_pck   = t_tcp;
                meta.udp_pck   = t_udp;
                meta.syn_pck   = t_syn;

                clone(CloneType.I2E, 500);

                reg_tot_pck.write(0, 0);
                reg_tot_bytes.write(0, 0);
                reg_tcp_pck.write(0, 0);
                reg_udp_pck.write(0, 0);
                reg_syn_pck.write(0, 0);
            }
        }
    }
}
