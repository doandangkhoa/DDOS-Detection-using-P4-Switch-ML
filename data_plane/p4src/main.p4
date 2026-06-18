#include <core.p4>
#include <v1model.p4>

// Include cấu trúc dữ liệu và parser
#include "includes/headers.p4"
#include "includes/parsers.p4"

// Include các khối xử lý chính
#include "ingress.p4"
#include "egress.p4"

// Khai báo các khối trống không sử dụng (bắt buộc theo chuẩn v1model)
control MyVerifyChecksum(inout headers hdr, inout metadata meta) { apply { } }
control MyComputeChecksum(inout headers hdr, inout metadata meta) { apply { } }

control MyDeparser(packet_out packet, in headers hdr) {
    apply {
        packet.emit(hdr.ethernet);
        packet.emit(hdr.ipv4);
        packet.emit(hdr.tcp);
        packet.emit(hdr.udp);
        packet.emit(hdr.telemetry); // Payload Telemetry xếp cuối gói tin
    }
}

// Khởi tạo Switch
V1Switch(
    MyParser(),
    MyVerifyChecksum(),
    MyIngress(),
    MyEgress(),
    MyComputeChecksum(),
    MyDeparser()
) main;

// cd ~/ddos-p4-rf-project/data_plane/p4src
// p4c-bm2-ss --p4v 16 --toJSON ../../topology/p4_compiled.json main.p4