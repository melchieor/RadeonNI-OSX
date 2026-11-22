#ifndef TEST_OWNER_BUFFER_H
#define TEST_OWNER_BUFFER_H
#include <stdint.h>
#include <libkern/c++/OSObject.h>
typedef uint32_t UInt32;typedef uint32_t IOByteCount;typedef uint32_t IOPhysicalAddress;
enum {kIODirectionInOut=3,kIOReturnSuccess=0};
class IOBufferMemoryDescriptor:public OSObject {
public:
 int complete_result;
 IOBufferMemoryDescriptor():complete_result(0){}
 static IOBufferMemoryDescriptor *withOptions(unsigned,unsigned,unsigned){return new IOBufferMemoryDescriptor;}
 int prepare(){return 0;}
 int complete(){return complete_result;}
 IOPhysicalAddress getPhysicalSegment(UInt32,IOByteCount *length){*length=4096;return 4096;}
};
#endif
