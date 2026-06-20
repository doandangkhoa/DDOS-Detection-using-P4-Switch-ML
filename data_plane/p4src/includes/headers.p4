#ifndef _HEADERS_P4_
#define _HEADERS_P4_

header ethernet_t {
    bit<48> dstAddr;
    bit<48> srcAddr;
    bit<16> etherType;
}

header ipv4_t {
    bit<4>  version;
    bit<4>  ihl;
    bit<8>  diffserv;
    bit<16> totalLen;
    bit<16> identification;
    bit<3>  flags;
    bit<13> fragOffset;
    bit<8>  ttl;
    bit<8>  protocol;
    bit<16> hdrChecksum;
    bit<32> srcAddr;
    bit<32> dstAddr;
}

header tcp_t {
    bit<16> srcPort;
    bit<16> dstPort;
    bit<32> seqNo;
    bit<32> ackNo;
    bit<4>  dataOffset;
    bit<3>  res;
    bit<3>  ecn;
    bit<6>  ctrl; 
    bit<16> window;
    bit<16> checksum;
    bit<16> urgentPtr;
}

header udp_t {
    bit<16> srcPort;
    bit<16> dstPort;
    bit<16> length;
    bit<16> checksum;
}

// Phải đồng bộ với sdn controller
header telemetry_report_t {
    bit<32> switch_id;
    bit<16> tot_pck;
    bit<32> tot_bytes;
    bit<16> tcp_pck;
    bit<16> udp_pck;
    bit<16> syn_pck;
    bit<32> victim_ip;
}

struct headers {
    ethernet_t         ethernet;
    ipv4_t             ipv4;
    tcp_t              tcp;
    udp_t              udp;
    telemetry_report_t telemetry;
}

struct metadata {
    @field_list(1)
    bit<16> tot_pck;
    @field_list(1)
    bit<32> tot_bytes;
    @field_list(1)
    bit<16> tcp_pck;
    @field_list(1)
    bit<16> udp_pck;
    @field_list(1)
    bit<16> syn_pck;
    @field_list(1)
    bit<32> victim_ip;
    bit<2>  meter_color;   // không cần giữ, nên không đánh dấu
}

#endif
