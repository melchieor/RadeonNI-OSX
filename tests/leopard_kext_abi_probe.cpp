// Compile-only ABI probe, never installed or executed on the G5.
// Apple PPC IOKit requires one destructor slot, a null vtable terminator,
// and the GCC 2.95 member-pointer representation.
class RDNABIProbe {
public:
    virtual ~RDNABIProbe();
    virtual void reserved();
    void plain();
} __attribute__((apple_kext_compatibility));
RDNABIProbe::~RDNABIProbe() {}
void RDNABIProbe::reserved() {}
void RDNABIProbe::plain() {}
void (RDNABIProbe::*rdn_abi_plain)() = &RDNABIProbe::plain;
void (RDNABIProbe::*rdn_abi_virtual)() = &RDNABIProbe::reserved;
