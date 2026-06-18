#include <core.p4>
#include <v1model.p4>
#include "includes/headers.p4"

control MyEgress(inout headers hdr, inout metadata meta, inout standard_metadata_t standard_metadata) {
    apply {
        if (hdr.ipv4.isValid()) {
            hdr.ipv4.identification = hdr.ipv4.identification + (bit<16>)standard_metadata.egress_port;
        }

        // Kiểm tra nếu là gói tin nhân bản (Clone Session 500)
        if (standard_metadata.instance_type == 1) { 
            
            // 1. Cấu hình Lớp mạng (UDP Telemetry)
            hdr.ethernet.dstAddr = 0x000000000005; 
            hdr.ipv4.dstAddr     = 0x0a000005;     // 10.0.0.5 (IP của h5)
            hdr.ipv4.protocol    = 17;             // UDP

            hdr.udp.setValid();
            hdr.udp.srcPort      = 50000;
            hdr.udp.dstPort      = 50000;
            
            // Độ dài UDP = 8 (header) + 14 (telemetry) = 22 bytes
            hdr.udp.length       = 22; 
            hdr.udp.checksum     = 0;              // Tắt kiểm tra checksum
	    hdr.udp.checksum     = (bit<16>)standard_metadata.egress_port + (bit<16>)standard_metadata.ingress_port;
            
            // 2. Điền dữ liệu Telemetry
            hdr.telemetry.setValid();
            hdr.telemetry.switch_id = 1;
            hdr.telemetry.tot_pck   = meta.tot_pck;
            hdr.telemetry.tot_bytes = meta.tot_bytes;
            hdr.telemetry.tcp_pck   = meta.tcp_pck;
            hdr.telemetry.udp_pck   = meta.udp_pck;
            hdr.telemetry.syn_pck   = meta.syn_pck;

            // 3. ĐỊNH TUYẾN RA PORT 5
            // Đây là cách duy nhất để đẩy gói tin clone ra ngoài switch
            standard_metadata.egress_spec = 5; 
        }
    }
}
