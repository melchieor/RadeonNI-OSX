#ifndef TEST_IOBUFFER_H
#define TEST_IOBUFFER_H
#include <stdint.h>
typedef uint32_t UInt32;
typedef uint32_t IOByteCount;
typedef uint32_t IOPhysicalAddress;
typedef uint32_t IOOptionBits;
enum {kIODirectionInOut=3,kIOReturnSuccess=0,kIOMemoryIncoherentIOFlush=1,kIOMemoryIncoherentIOStore=2};
extern int mock_create_fail,mock_prepare_fail,mock_complete_fail,mock_segment_fail;
extern int mock_prepares,mock_completes,mock_releases;
extern uint32_t mock_mapped_base;
extern int mock_operation_fail,mock_operation_calls;
extern uint32_t mock_last_operation;
class IOBufferMemoryDescriptor {
 uint32_t storage[1024];
public:
 static IOBufferMemoryDescriptor *withOptions(unsigned,unsigned,unsigned) {return mock_create_fail?0:new IOBufferMemoryDescriptor;}
 int prepare(){++mock_prepares;return mock_prepare_fail?-1:0;}
 int complete(){++mock_completes;return mock_complete_fail?-1:0;}
 int performOperation(IOOptionBits op,IOByteCount off,IOByteCount len){++mock_operation_calls;mock_last_operation=op;return mock_operation_fail || off || len!=4096?-1:0;}
 void release(){++mock_releases;delete this;}
 IOPhysicalAddress getPhysicalSegment(UInt32 offset,IOByteCount *length){*length=mock_segment_fail?0:4096;return mock_mapped_base+offset;}
 void *getBytesNoCopy(){return storage;}
};
#endif
