#include <core.p4>
#include <v1model.p4>
#include "includes/headers.p4"

// ===== HEAVY HITTER SKETCH: tìm victim không cần biết trước IP =====
// M = số slot trong hash table. Tăng M để giảm xác suất đụng độ (trade-off
// giữa độ chính xác và số lượng register cần dùng), không liên quan gì
// đến số IP thật trong mạng — đây là tham số kỹ thuật của thuật toán.
#define SKETCH_SIZE 8


control MyIngress(inout headers hdr, inout metadata meta, inout standard_metadata_t standard_metadata) {
    
    // 1. KHAI BÁO BIẾN TRẠNG THÁI (REGISTERS & METERS)
    register<bit<16>>(1) reg_tot_pck;
    register<bit<32>>(1) reg_tot_bytes;
    register<bit<16>>(1) reg_tcp_pck;
    register<bit<16>>(1) reg_udp_pck;
    register<bit<16>>(1) reg_syn_pck;

    register<bit<32>>(SKETCH_SIZE) syn_slot_ip;     // IP nào đang "chiếm" slot này
    register<bit<16>>(SKETCH_SIZE) syn_slot_count;  // SYN count của IP đó trong window

    register<bit<32>>(1) reg_victim_ip;    // kỷ lục toàn cục: IP bị SYN nhiều nhất
    register<bit<16>>(1) reg_victim_count; // kỷ lục toàn cục: giá trị đếm tương ứng

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

                    // --- Bước 1: băm dstAddr ra index trong bảng sketch ---
                    bit<32> idx;
                    hash(idx, HashAlgorithm.crc32, (bit<32>)0,
                        { hdr.ipv4.dstAddr }, (bit<32>)SKETCH_SIZE);

                    // --- Bước 2: đọc trạng thái slot hiện tại ---
                    bit<32> slot_ip;
                    bit<16> slot_cnt;
                    syn_slot_ip.read(slot_ip, idx);
                    syn_slot_count.read(slot_cnt, idx);

                    if (slot_ip == hdr.ipv4.dstAddr) {
                        // Cùng IP đang chiếm slot -> tăng đếm bình thường
                        slot_cnt = slot_cnt + 1;
                    } else {
                        // Slot trống hoặc bị IP khác chiếm (đụng độ hash, hiếm gặp
                        // nếu SKETCH_SIZE đủ lớn) -> IP mới giành lại slot, reset về 1
                        slot_ip  = hdr.ipv4.dstAddr;
                        slot_cnt = 1;
                    }

                    syn_slot_ip.write(idx, slot_ip);
                    syn_slot_count.write(idx, slot_cnt);

                    // --- Bước 3: cập nhật kỷ lục toàn cục ngay lúc này, không cần quét lại ---
                    bit<16> cur_max;
                    reg_victim_count.read(cur_max, 0);
                    if (slot_cnt > cur_max) {
                        reg_victim_count.write(0, slot_cnt);
                        reg_victim_ip.write(0, slot_ip);
                    }
                }
            } else if (hdr.udp.isValid()) {
                t_udp = t_udp + 1;
            }

            reg_tot_pck.write(0, t_pck);
            reg_tot_bytes.write(0, t_bytes);
            reg_tcp_pck.write(0, t_tcp);
            reg_udp_pck.write(0, t_udp);
            reg_syn_pck.write(0, t_syn);

            if (t_pck >= 10000) { 
                bit<32> v_ip;
                bit<16> v_cnt;
                reg_victim_ip.read(v_ip, 0);
                reg_victim_count.read(v_cnt, 0);

                meta.tot_pck   = t_pck;
                meta.tot_bytes = t_bytes;
                meta.tcp_pck   = t_tcp;
                meta.udp_pck   = t_udp;
                meta.syn_pck   = t_syn;
                meta.victim_ip = v_ip;

                clone_preserving_field_list(CloneType.I2E, 500, 1);

                reg_tot_pck.write(0, 0);
                reg_tot_bytes.write(0, 0);
                reg_tcp_pck.write(0, 0);
                reg_udp_pck.write(0, 0);
                reg_syn_pck.write(0, 0);

                // Reset kỷ lục toàn cục cho window kế tiếp
                reg_victim_ip.write(0, 0);
                reg_victim_count.write(0, 0);

                // Reset bảng sketch
                syn_slot_count.write(0, 0);
                syn_slot_count.write(1, 0);
                syn_slot_count.write(2, 0);
                syn_slot_count.write(3, 0);
                syn_slot_count.write(4, 0);
                syn_slot_count.write(5, 0);
                syn_slot_count.write(6, 0);
                syn_slot_count.write(7, 0);

                syn_slot_ip.write(0, 0);
                syn_slot_ip.write(1, 0);
                syn_slot_ip.write(2, 0);
                syn_slot_ip.write(3, 0);
                syn_slot_ip.write(4, 0);
                syn_slot_ip.write(5, 0);
                syn_slot_ip.write(6, 0);
                syn_slot_ip.write(7, 0);
            }
        }
    }
}
